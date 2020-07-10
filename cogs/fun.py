import logging

import discord
from discord.ext import commands


class Fun(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Fun')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Fun')
    
    @commands.command()
    async def send(self, ctx, channel: discord.TextChannel = None, *, message:str = None):
        """ Send message to some channel """

        if channel is None:
            return await ctx.send('Please enter channel name.')
        
        if message is None:
            return await ctx.send('Please enter message.')

        await channel.send(message)

def setup(bot):
    bot.add_cog(Fun(bot))

