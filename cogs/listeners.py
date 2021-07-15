import asyncio
import logging

import discord
from discord.ext import commands

from helper import NoAuthority

class Errors(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Listeners')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Error listener')
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, err):

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

        elif isinstance(err,NoAuthority):
            await ctx.message.add_reaction('<:kgsStop:579824947959169024>')

        elif isinstance(err,commands.errors.BadArgument):
            await ctx.send(f'```{err}```',delete_after=6)
            await asyncio.sleep(6)
            await ctx.message.delete()

        else:
            self.logger.err(str(err))
            return await ctx.send("Can't execute the command!!")

def setup(bot):
    bot.add_cog(Errors(bot))

