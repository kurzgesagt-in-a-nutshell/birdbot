import io
import asyncio
import logging
import math
import textwrap
import traceback
import subprocess
import os
import dotenv
from contextlib import redirect_stdout

import discord
from discord.ext import commands

from kurzgesagt import args
from helper import mod_and_above

dotenv.load_dotenv()

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

    @commands.group(hidden=True,aliases=['presence'])
    @commands.is_owner()
    async def activity(self, ctx):
        """Sets the bots status"""
        pass

    async def change_activity(self, ctx, activity):
        await ctx.bot.change_presence(status=ctx.guild.me.status, activity=activity)
        await ctx.send(' presence changed.')

    @activity.command(aliases=['l'])
    @commands.is_owner()
    async def listening(self, ctx, *, text):
        """Set listening activity"""
        audio = discord.Activity(
            name=text, type=discord.ActivityType.listening)
        await self.change_activity(ctx, audio)

    @activity.command(aliases=['w'])
    @commands.is_owner()
    async def watching(self, ctx, *, text):
        """Set watching activity"""
        video = discord.Activity(name=text, type=discord.ActivityType.watching)
        await self.change_activity(ctx, video)

    @activity.command(aliases=['p'])
    @commands.is_owner()
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
                self.logger.info(
                    f'Output chars: {len(str(value)) + len(str(ret))}')
                self._last_result = ret
                if len(str(value)) + len(str(ret)) >= 2000:
                    await ctx.send(f'Returned over 2k chars, sending as file instead.\n'
                                   f'(first 1.5k chars for quick reference)\n'
                                   f'```py\n{f"{value}{ret}"[0:1500]}\n```',
                                   file=discord.File(io.BytesIO(f'{value}{ret}'.encode()),
                                                     filename='output.txt'))
                else:
                    await ctx.send(f'```py\n{value}{ret}\n```')

    @commands.is_owner()
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
        os.environ['FORCIBLY_KILLED'] = '1'
        await ctx.send('Bravo 6 going dark')
        await self.bot.logout()

    @commands.is_owner()
    @commands.command(hidden=True)
    async def pull(self,ctx):
        self.logger.info('pulling repository')
        await asyncio.create_subprocess_shell('git fetch')
        proc = await asyncio.create_subprocess_shell('git pull',
                                                     stdout=asyncio.subprocess.PIPE,
                                                     stderr=asyncio.subprocess.STDOUT)
        output = await proc.communicate()
        if len(output[0].decode()) > 2000:
            self.logger.info('Output too large, sending a file instead')
            file = discord.File(io.BytesIO(output[0]),filename='output.txt')
            await ctx.send('Pull output',file= file)
        else:
            await ctx.send(f"```{output[0].decode()}```")

        #check for reaction call
        def check(reaction,user):
            return user == ctx.author and str(reaction.emoji) in ('<:kgsYes:580164400691019826>','<:kgsNo:610542174127259688>')

        #if no error is found in pulling, ask if restart is needed
        #DOES NOT WORK FOR BETA INSTANCE
        if output[1] is None and not args.beta:
            m = await ctx.send('Would you like to restart the bot instance?')
            await m.add_reaction('<:kgsYes:580164400691019826>')
            await m.add_reaction('<:kgsNo:610542174127259688>')
            try:
                reaction, user = await self.bot.wait_for('reaction_add',timeout=20.0,check=check)  
            except asyncio.TimeoutError:
                await m.delete()
                return
            if str(reaction.emoji) == '<:kgsYes:580164400691019826>':
                await self.bot.close()
            elif str(reaction.emoji) == '<:kgsNo:610542174127259688>':
                await m.delete()
                    
def setup(bot):
    bot.add_cog(Dev(bot))
