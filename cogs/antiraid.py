import logging
import datetime

import discord
from discord.ext import commands

from utils.helper import mod_and_above, devs_only


class Antiraid(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Antiraid')
        self.bot = bot
        self.raidon = False
        self.raidinfo = (0, 0)
        self.newjoins = []
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Antiraid')
    
    @devs_only()
    @commands.command()
    async def raidmode(self, ctx, joins: int, per_second: int):
        """
        Turns the anti-raid mode on
        Usage: raidmode joins per_second
        """
        if joins > 100:
            raise commands.BadArgument(message="Can't do more than 100 joins")
        self.raidinfo = (joins, per_second)
        await ctx.send(f'Set raidmode when there are {joins} joins every {per_second} seconds.')

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != 414027124836532234:
            return
        if member.bot:
            return

        self.newjoins.append(member.joined_at)

        len_newjoins = len(self.newjoins)

        if len_newjoins >= 101:
            i = len_newjoins-100 
            del len_newjoins[0:i]
            len_newjoins -= 1
    	
        if self.raidon and self.raidinfo[0] >= len_newjoins:
            index = len_newjoins-self.raidinfo[0]
            if self.newjoins[index]-member.joined_at > datetime.timedelta(seconds=self.raidinfo(1)):
                await member.send("The Kurzgesagt - In a Nutshell server is currently under a raid. You were kicked as a precaution, if you did not take part in the raid try joining again in an hour!")
                await member.kick(reason="Raid counter")




def setup(bot):
    bot.add_cog(Antiraid(bot))
