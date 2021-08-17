import datetime
import logging

import discord
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Help')
        self.bot = bot
        self.bot.remove_command('help')

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Help')

    @commands.command(aliases=['h'])
    async def help(self, ctx, *, cmnd=None):
        """
            Display help. \nUsage: help command_name
        """

        cogs = list(self.bot.cogs)
        cogs.remove('Dev')
        cogs.remove('Errors')

        if cmnd is None:
            embed = discord.Embed(title="Kurzbot Help", description=f'To see more info do help [command].',
                                  color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
            for i in cogs:
                cog = self.bot.get_cog(i)
                cmd_list = []
                for command in cog.walk_commands():
                    if not command.hidden:
                        if command.parent is None:
                            cmd_list.append(f"`{command.name}`")
                        else:
                            cmd_list.append(
                                f"`{command.parent.name} {command.name}`"
                            )

                embed.add_field(name=i, value='\n'.join(cmd_list))

            return await ctx.send(embed=embed)

        else:
            c = self.bot.get_command(cmnd)
            if c is not None and c.cog_name in cogs:
                command = self.bot.get_command(cmnd)
                embed = discord.Embed(title=command.name, description=f'```{command.help}```',
                                      color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
                if command.aliases:
                    embed.add_field(
                        name='Alias', value=f'```{", ".join(command.aliases)}```', inline=False)
                return await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        """
            Ping Pong
        """
        await ctx.send(f'{int(self.bot.latency * 1000)} ms')


def setup(bot):
    bot.add_cog(Help(bot))
