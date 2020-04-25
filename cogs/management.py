import discord
from discord.ext import commands


class Management(commands.Cog, name='Management'):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('loaded management')
    
    @commands.has_any_role('Galacduck', 'Administrator')
    @commands.command()
    async def send(self, ctx, channel, *, string):
        msgchannelstr = discord.utils.get(self.bot.get_guild(414027124836532234).channels, name=channel)
        await msgchannel.send(string)


def setup(bot):
    bot.add_cog(Management(bot))