import logging

import discord
from discord.ext import commands


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Moderation')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Moderation')
    
    @commands.command()
    async def your_command(self, ctx):
        """Command description"""
        await ctx.send('thing')


def setup(bot):
    bot.add_cog(Moderation(bot))

