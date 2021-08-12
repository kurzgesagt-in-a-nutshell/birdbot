import io
import asyncio
import logging
import math
import textwrap
import traceback
import os

from contextlib import redirect_stdout

from git import Repo
from git.cmd import Git

import discord
from discord.ext import commands

from utils.helper import mod_and_above, devs_only, mainbot_only


class Dev(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Dev')
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Dev')

    def cleanup_code(self, content):
        """
            Remove code-block from eval
        """
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        return content.strip('`\n')

    def get_syntax_error(self, e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    @commands.group(hidden=True, aliases=['presence'])
    @devs_only()
    async def activity(self, ctx):
        """Sets the bots status"""
        pass

    async def change_activity(self, ctx, activity):
        await ctx.bot.change_presence(activity=activity)
        await ctx.send(' presence changed.')

    @activity.command(aliases=['l'])
    @devs_only()
    async def listening(self, ctx, *, text):
        """Set listening activity"""
        audio = discord.Activity(name=text,
                                 type=discord.ActivityType.listening)
        await self.change_activity(ctx, audio)

    @activity.command(aliases=['w'])
    @devs_only()
    async def watching(self, ctx, *, text):
        """Set watching activity"""
        video = discord.Activity(name=text, type=discord.ActivityType.watching)
        await self.change_activity(ctx, video)

    @activity.command(aliases=['p'])
    @devs_only()
    async def playing(self, ctx, *, text):
        """Set playing activity"""
        game = discord.Activity(name=text, type=discord.ActivityType.playing)
        await self.change_activity(ctx, game)

    @commands.is_owner()
    @commands.command(pass_context=True, name='eval')
    async def eval(self, ctx, *, body: str):
        """Evaluates a code"""
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'self': self,
            'math': math,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('<:kgsYes:580164400691019826>')
            except Exception as _:
                await ctx.message.add_reaction('<:kgsNo:610542174127259688>')
                pass

            if ret is None:
                self.logger.info(f'Output chars: {len(str(value))}')
                if value:
                    if len(str(value)) >= 2000:
                        await ctx.send(
                            f'Returned over 2k chars, sending as file instead.\n'
                            f'(first 1.5k chars for quick reference)\n'
                            f'```py\n{value[0:1500]}\n```',
                            file=discord.File(io.BytesIO(value.encode()),
                                              filename='output.txt'))
                    else:
                        await ctx.send(f'```py\n{value}\n```')
            else:
                self.logger.info(
                    f'Output chars: {len(str(value)) + len(str(ret))}')
                self._last_result = ret
                if len(str(value)) + len(str(ret)) >= 2000:
                    await ctx.send(
                        f'Returned over 2k chars, sending as file instead.\n'
                        f'(first 1.5k chars for quick reference)\n'
                        f'```py\n{f"{value}{ret}"[0:1500]}\n```',
                        file=discord.File(io.BytesIO(f'{value}{ret}'.encode()),
                                          filename='output.txt'))
                else:
                    await ctx.send(f'```py\n{value}{ret}\n```')

    @devs_only()
    @commands.command(name='reload', hidden=True)
    async def reload(self, ctx, *, module: str = None):
        ''' Reload a module '''
        try:
            if module is None:
                return await ctx.send('**Usage:** `reload module_name`')
            try:
                self.bot.unload_extension(module)
            except discord.ext.commands.errors.ExtensionNotLoaded as enl:
                self.logger.exception('Module not loaded.')

            self.bot.load_extension(module)
            await ctx.send('Module Loaded')

        except Exception as e:
            self.logger.error('Unable to load module.')
            self.logger.error('{}: {}'.format(type(e).__name__, e))

    @commands.command(hidden=True)
    @mod_and_above()
    async def kill(self, ctx):
        """Kill the bot"""
        await ctx.send('Bravo 6 going dark.')
        await self.bot.close()

    @commands.command()
    @devs_only()
    @mainbot_only()
    async def launch(self, ctx, instance: str):
        """Spawn child process of alpha/beta bot instance on the VM, only works on main bot"""

        if instance not in ('alpha', 'beta'):
            raise commands.BadArgument(
                "Instance argument must be `alpha` or `beta`")

        try:
            child = await asyncio.create_subprocess_shell(
                'python3 startbot.py --{}'.format(instance),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT)
            await ctx.send(
                f"Loaded {instance} instance. Don't forget to kill the instance once you're done to prevent memory leaks"
            )
            await child.wait()

        finally:
            try:
                await ctx.send(f"{instance} instance has been terminated")
                await child.terminate()
            except ProcessLookupError:
                pass

    @devs_only()
    @commands.command(hidden=True)
    async def pull(self, ctx):
        self.logger.info('pulling repository')
        repo = Repo(os.getcwd())  #Get git repo object to check changes
        assert not repo.bare
        if repo.is_dirty():
            return await ctx.send(
                'There are untracked changes on the branch, please resolve them before pulling'
            )

        _g = Git(os.getcwd())
        _g.fetch()
        message = _g.pull('origin', 'master')
        await ctx.send(f"```{message}```")


def setup(bot):
    bot.add_cog(Dev(bot))
