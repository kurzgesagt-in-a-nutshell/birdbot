import logging
import datetime
import typing

import discord
from discord.ext import commands

from utils.helper import mod_and_above, devs_only


class Antiraid(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Antiraid")
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Antiraid")
        self.raidon = False
        self.raidinfo = (0, 0)
        self.newjoins = []
        self.blacklist = ["clonex"]

    @devs_only()
    @commands.command()
    async def raidmode(self, ctx, joins: int, in_seconds: int):
        """
        Turns the anti-raid mode on
        Usage: on/off raidmode joins in_seconds
        """
        if joins > 100:
            raise commands.BadArgument(message="Can't do more than 100 joins.")
        self.raidinfo = (joins, in_seconds)
        self.raidon = True
        await ctx.send(
            f"Set raidmode when there are {joins} joins every {in_seconds} seconds."
        )

    @devs_only()
    @commands.command()
    async def raidoff(self, ctx):
        """
        Turns the anti-raid mode off
        Usage: raidoff
        """
        self.raidon = False

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != 414027124836532234:
            return
        if member.bot:
            return

        self.newjoins.append(member.joined_at)

        if len(self.newjoins) >= 101:
            i = len(self.newjoins) - 100
            del self.newjoins[0:i]

        len_newjoins = len(self.newjoins)

        if self.raidon and len_newjoins >= self.raidinfo[0]:
            index = len_newjoins - self.raidinfo[0]
            if member.joined_at - self.newjoins[index] < datetime.timedelta(
                seconds=self.raidinfo[1]
            ):
                await member.send(
                    "The Kurzgesagt - In a Nutshell server is currently under a raid. You were kicked as a precaution, if you did not take part in the raid try joining again in an hour!"
                )
                await member.kick(reason="Raid counter")
                return

            if member.joined_at - self.newjoins[-2] > datetime.timedelta(minutes=5):
                self.raidon = False

        for i in self.blacklist:
            if member.name in i:
                await member.kick(reason="Blacklisted name, probably a bot")


def setup(bot):
    bot.add_cog(Antiraid(bot))
