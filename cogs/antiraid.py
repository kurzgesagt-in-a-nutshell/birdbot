import logging
import datetime

import discord
from discord.ext import commands

from utils.helper import mod_and_above, devs_only


class Antiraid(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Antiraid')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Antiraid')
        self.raidon = False
        self.raidinfo = (0, 0)
        self.newjoins = []
        self.blacklist = ["clonex"]
    
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

    @devs_only()
    @commands.command()
    async def raidoff(self, ctx):
        """
        Turns the anti-raid mode off
        Usage: raidoff
        """
        await ctx.send(f'Turns raidemode off')


    @devs_only()
    @commands.command()
    async def raidoff(self, ctx):
        """
        Turns the anti-raid mode off
        Usage: raidoff
        """
        await ctx.send(f'Turns raidemode off')

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
            len_newjoins = 100
    	
        if self.raidon and len_newjoins >= self.raidinfo[0]:
            index = len_newjoins-self.raidinfo[0]
            if self.newjoins[index]-member.joined_at < datetime.timedelta(seconds=self.raidinfo[1]):
                await member.send("The Kurzgesagt - In a Nutshell server is currently under a raid. You were kicked as a precaution, if you did not take part in the raid try joining again in an hour!")
                await member.kick(reason="Raid counter")

            if self.self.newjoins[index]-member.joined_at > datetime.timedelta(minutes = 5):
                self.raidon = False

        for i in self.blacklist:
            if member.name in i:
                await member.kick(reason="Blacklisted name, probably a bot")




def setup(bot):
    bot.add_cog(Antiraid(bot))
