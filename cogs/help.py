import re
import json

import discord
from discord.ext import commands


class Help(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={'help': 'The help command'})
        self.config = json.load(open('config.json'))

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title='Commands list', color=0xbbfcac,
                              description=f"You can get the commands ")
        for i in mapping:
            if len(mapping[i]) == 0 or i is None:
                continue
            embed.add_field(name=f'{i.qualified_name if i is not None else "None"} [{len(mapping[i])}]',
                            value=f'`{self.clean_prefix}help {i.qualified_name if i is not None else "None"}`')
        embed.set_author(icon_url=self.context.bot.user.avatar_url, name='')
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        # get_command_signature = usage string
        if command.cog.qualified_name == 'Owner':
            if self.context.author.id not in self.config['owners']:
                await self.get_destination().send('<:feel:699157483477794899> Don\'t even try.')
                return
        help_raw = command.help if command.help is not None else "No description."
        h_pattern = re.compile(r'Example\s?\d*: ?[^\n]+')
        help_stripped = re.sub(h_pattern, '', help_raw)
        embed = discord.Embed(
            title=f"{self.clean_prefix}{command.name}",
            description=help_stripped,
            color=0xd4f7ab
        )
        embed.set_author(name=f"{self.context.bot.user.name}'s Help Desk",
                         icon_url=self.context.bot.user.avatar_url)

        embed.add_field(name="Usage", value='``' +
                        self.get_command_signature(command)+'``',
                        inline=False)

        embed.add_field(name='Aliases', value=' '.join(
            f'`{i}`' for i in command.aliases) if len(command.aliases) != 0 else "None",
            inline=False)

        embed.add_field(name='Group/Cog', value=command.cog.qualified_name,inline=False)

        examples = []
        pattern = re.compile(r'Example\s?\d*: ?(?P<example>.+)')
        matches = re.finditer(pattern, help_raw)
        for i in matches:
            examples.append('`'+self.clean_prefix+i.groupdict()['example']+'`')

        embed.add_field(name='Example(s)', value='\n'.join(
            f'{i}' for i in examples) if len(examples) != 0 else "No examples yet.",
            inline=False)

        embed.set_footer(
            text=f"Executed by user {self.context.author.name}", icon_url=self.context.author.avatar_url)
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog):
        if cog.qualified_name == 'Owner':
            await self.get_destination().send('Currently not available')
            return
        embed = discord.Embed(
            title=f'Commands in {cog.qualified_name}', description=cog.description, color=0xcef7ab)
        commands = []
        for i in cog.get_commands():
            commands.append(i)
        embed.add_field(name='Commands', value='\n'.join(
                        f'`{self.clean_prefix}{i.name}` - {i.help.splitlines()[0] if i.help is not None else "None"}' for i in commands))
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        if group.cog.qualified_name == 'Owner':
            if self.context.author.id not in self.config['owners']:
                await self.get_destination().send('<:feel:699157483477794899> Don\'t even try.')
                return
        embed = discord.Embed(
            color=0xbfec8d, title=f'Subcommands for {group.name}')
        embed.description = '`'+str(self.get_command_signature(group))+'[subcommands]`'
        commands = []
        for i in group.commands:
            commands.append(i)
        embed.add_field(name="Commands", value='\n'.join(
            f'`{self.clean_prefix}{i.qualified_name}` - {i.help.splitlines()[0] if i.help is not None else "None"}'
            for i in commands) if len(commands) != 0 else "No sub-commands"
        )
        await self.get_destination().send(embed=embed)

    def command_not_found(self, string):
        # Returns when the command is not found.
        return f'CommandNotFound,{string}'

    def subcommand_not_found(self, command, string):
        return f'SubcommandNotFound,{command.name},{string}'

    async def send_error_message(self, err):
        parsed_err = err.split(',')
        if parsed_err[0] == 'CommandNotFound':
            embed = discord.Embed(color=0xf85c4d, title='Command not found',
                                  description=f"No command called {parsed_err[1]} is found. Please check if y"
                                              f"ou have made any typos and try again. You can see the "
                                              f"command list with `{self.clean_prefix}help`\n")
            await self.get_destination().send(embed=embed)
        elif parsed_err[0] == 'SubcommandNotFound':
            embed = discord.Embed()
            embed.colour = 0xf85c4d
            embed.description = f"There is no subcommand in the command {parsed_err[1]} " \
                                f"or there is no subcommand called {parsed_err[2]}. Check {self.clean_prefix}"\
                                f"help {parsed_err[1]}"
            await self.get_destination().send(embed=embed)
        else:
            await self.get_destination().send(err)

    async def command_callback(self, ctx, *, command=None):
        await self.prepare_help_command(ctx, command)
        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        # Check if it's a cog
        for i in self.get_bot_mapping():
            if i is None:
                continue
            name = i.qualified_name.lower()
            if name.startswith(command.lower()):
                return await self.send_cog_help(i)

        maybe_coro = discord.utils.maybe_coroutine

        # If it's not a cog then it's a command.
        # Since we want to have detailed errors when someone
        # passes an invalid subcommand, we need to walk through
        # the command group chain ourselves.
        keys = command.split(' ')
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)


def setup(bot):
    bot.help_command = Help()
