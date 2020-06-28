import logging

import discord
from discord.ext import commands

from discord.message import Embed


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Moderation')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Moderation')
    
    
    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def clean(self, ctx, msg_count: int=None):
        """ Clean messages """
        if msg_count is None:
            await ctx.send(f' ***Enter number of messages*** (k!clean message_count) ')
        
        elif msg_count > 200:
            await ctx.send(f'Provided number is too big. (Max limit 200)')

        else:
            await ctx.channel.purge(limit=msg_count+1)


def setup(bot):
    bot.add_cog(Moderation(bot))

