import os
import io
import sys
import time
import copy
import json
import pickle
import inspect
import asyncio
import aiohttp
import textwrap
import traceback
from typing import Union, Optional
from subprocess import Popen, PIPE, run
from contextlib import redirect_stdout

import discord
from discord.ext import commands

# to expose to the eval command
import datetime
from collections import Counter

# Bot wide config.
config = json.load(open('config.json'))

class GlobalChannel(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            return await commands.TextChannelConverter().convert(ctx, argument)
        except commands.BadArgument:
            # Not found... so fall back to ID + global lookup
            try:
                channel_id = int(argument, base=10)
            except ValueError:
                raise commands.BadArgument(
                    f'Could not find a channel by ID {argument!r}.')
            else:
                channel = ctx.bot.get_channel(channel_id)
                if channel is None:
                    raise commands.BadArgument(
                        f'Could not find a channel by ID {argument!r}.')
                return channel


class Owner(commands.Cog, name="Owner", command_attrs=dict(hidden=True)):
    """Owner-only commands that make the bot dynamic.
    Made by: Rapptz"""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = set()

    @commands.Cog.listener()
    async def on_ready(self):
        print('loaded owner')

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    async def cog_check(self, ctx):
        return ctx.author.id == (await ctx.bot.application_info()).owner.id or \
            ctx.author.id == 521656100924293141 or \
            ctx.author.id in config['owners']

    def get_syntax_error(self, e):
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'
        
    @commands.command(pass_context=True, hidden=True, name='eval')
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self._last_result
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
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')
            
    @commands.command(aliases=['pull'])
    async def gitpull(self, ctx):
        """Updates the local code from github"""
        m = await ctx.send('Pulling repository')
        run(['git', 'pull'])
        await m.edit(content='Assuming you do not have any conflicts, the local repo is now updated to '
                             'the branch the local repo was in.')
    @commands.command(hidden=True, aliases=['reboot', 'reload'])
    async def restart(self, ctx):
        """Restart the bot instance."""
        m = await ctx.send('<a:cypherspin:700826407554646038> Restarting')
        _ = Popen(["python3", 'main.py'])
        await m.edit(content='<a:cypherspin:700826407554646038> Started new python instance.')
        with open('__tmp_restart__.tmp', 'w+') as f:
            f.write(f'{ctx.channel.id},{time.time()}')
        await ctx.bot.close()
                
def setup(bot):
    bot.add_cog(Owner(bot))
