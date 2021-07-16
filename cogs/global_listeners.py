import asyncio
import json

import logging
from traceback import TracebackException

import discord
from discord.ext import commands

from helper import NoAuthority

class Errors(commands.Cog):
    def __init__(self, bot):
        with open('config.json', 'r') as config_file:
            self.config_json = json.loads(config_file.read())
        self.dev_logging_channel = self.config_json['logging']['logging_channel']

        self.logger = logging.getLogger('Listeners')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Error listener')
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, err):
        traceback_txt = ''.join(TracebackException.from_exception(err).format())
        channel = self.bot.fetch_channel(dev_logging_channel)

        if isinstance(err, commands.errors.MissingPermissions):
            await ctx.message.add_reaction('<:kgsNo:610542174127259688>')

        elif isinstance(err, commands.MissingRequiredArgument):
            await ctx.send(f"You're missing the {err.param.name} argument. Please check syntax using help command.",delete_after=6)
            asyncio.sleep(6)
            await ctx.message.delete()

        elif isinstance(err, commands.CommandNotFound):
            pass

        elif isinstance(err, commands.errors.CommandOnCooldown):
            await ctx.message.add_reaction('\U000023f0')
            await asyncio.sleep(4)
            await ctx.message.delete()

        elif isinstance(err,NoAuthority):
            await ctx.message.add_reaction('<:kgsNo:610542174127259688>')

        elif isinstance(err,commands.errors.BadArgument):
            await ctx.send(f'```{err}```',delete_after=6)
            await asyncio.sleep(6)
            await ctx.message.delete()

        else:
            await ctx.message.add_reaction('<:kgsStop:579824947959169024>')
            await ctx.send("An unhandled exception occured, if this issue persists please contact FC or sloth")

            

def setup(bot):
    bot.add_cog(Errors(bot))

