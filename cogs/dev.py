import io
import copy
import math
import json
import time
import asyncio
import inspect
import logging
import textwrap
import traceback
from typing import Optional
from contextlib import redirect_stdout
from subprocess import PIPE, STDOUT, Popen, run

import discord
from discord.ext import commands


class Dev(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Dev')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Dev')

    def cleanup_code(self,content):
        """Remove codeblock from eval"""
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        return content.strip('`\n')

    async def cog_check(self, ctx):
        return ctx.author.id in self.bot.owner_ids

    def get_syntax_error(self, e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    @commands.group(hidden=True)
    async def activity(self, ctx):
        """Sets the bots status
        """
        await ctx.send_help(str(ctx.command))

    async def change_activity(self, ctx, activity):
        await ctx.bot.change_presence(status=ctx.guild.me.status, activity=activity)
        await ctx.send(' presence changed.')

    @activity.command(aliases=['l'])
    async def listening(self, ctx, *, text):
        """Set listening activity"""
        audio = discord.Activity(name=text, type=discord.ActivityType.listening)
        await self.change_activity(ctx, audio)

    @activity.command(aliases=['w'])
    async def watching(self, ctx, *, text):
        """Set watching activity"""
        video = discord.Activity(name=text, type=discord.ActivityType.watching)
        await self.change_activity(ctx, video)

    @activity.command(aliases=['p'])
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
                        await ctx.send(f'Returned over 2k chars, sending as file instead.\n'
                                       f'(first 1.5k chars for quick reference)\n'
                                       f'```py\n{value[0:1500]}\n```',
                                       file=discord.File(io.BytesIO(value.encode()),
                                                         filename='output.txt'))
                    else:
                        await ctx.send(f'```py\n{value}\n```')
            else:
                self.logger.info(f'Output chars: {len(str(value)) + len(str(ret))}')
                self._last_result = ret
                if len(str(value)) + len(str(ret)) >= 2000:
                    await ctx.send(f'Returned over 2k chars, sending as file instead.\n'
                                   f'(first 1.5k chars for quick reference)\n'
                                   f'```py\n{f"{value}{ret}"[0:1500]}\n```',
                                   file=discord.File(io.BytesIO(f'{value}{ret}'.encode()),
                                                     filename='output.txt'))
                else:
                    await ctx.send(f'```py\n{value}{ret}\n```')


def setup(bot):
    bot.add_cog(Dev(bot))

