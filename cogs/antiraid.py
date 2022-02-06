import logging
import datetime
import typing
import json

import discord
from discord.ext import commands
from birdbot import BirdBot

from utils.helper import mod_and_above, devs_only


class Antiraid(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Antiraid")
        self.bot = bot
        with open("config.json", "r") as config_file:
            config_json = json.loads(config_file.read())
        self.logging_channel = config_json["logging"]["logging_channel"]
        with open("antiraid.json", "r") as config_file:
            antiraid_json = json.loads(config_file.read())
        self.raidinfo = antiraid_json["raidmode"]
        self.newjoins = []
        self.blacklist = ["clonex"] #temporary clonex fix, develop into a proper feature?

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Antiraid")

    @devs_only()
    @commands.command()
    async def raidmode(self, ctx, joins: typing.Optional[int] = None, during: typing.Optional[int] = None):
        """
        Turns the anti-raid mode on
        Usage: on/off raidmode joins during
        """
        if not (joins and during):
            await ctx.send(f'Raidmode will activate when there are {self.raidinfo["joins"]} joins every {self.raidinfo["during"]} seconds.')
            return

        if joins > 100:
            raise commands.BadArgument(message="Can't do more than 100 joins.")

        self.raidinfo = {"joins": joins, "during": during}
        with open("antiraid.json", "w") as config_file:
            json.dump({"raidmode": self.raidinfo}, config_file, indent=4)
        await ctx.send(
            f"Set raidmode when there are {joins} joins every {during} seconds."
        )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != 414027124836532234:
            return
        if member.bot:
            return

        self.newjoins.append({"id":member.id, "time": member.joined_at})

        if len(self.newjoins) >= 101:
            i = len(self.newjoins) - 100
            del self.newjoins[0:i]

        if len(self.newjoins) >= self.raidinfo["joins"]:
            index = -self.raidinfo["joins"]
            if member.joined_at - self.newjoins[index]["time"] < datetime.timedelta(
                seconds=self.raidinfo["during"]
            ):
                try:
                    await member.send(
                        "The Kurzgesagt - In a Nutshell server might currently be under a raid. You were kicked as a precaution, if you did not take part in the raid try joining again in an hour!"
                    )
                except:
                    pass
                await member.kick(reason="Raid counter")

                if not BirdBot.currently_raided:
                    server = member.guild
                    await server.get_channel(self.logging_channel).send("Detected a raid.")
                    firstbots = self.newjoins[-index:]
                    for memberid in firstbots:
                        member = await server.get_member(memberid["id"])
                        if member.pending:
                            try:
                                await member.send(
                                    "The Kurzgesagt - In a Nutshell server might currently be under a raid. You were kicked as a precaution, if you did not take part in the raid try joining again in an hour!"
                                )
                            except:
                                pass
                            try:
                                await member.kick(reason="Raid counter")
                            except:
                                pass
                BirdBot.currently_raided = True
                return
            else:
                BirdBot.currently_raided = False

        for i in self.blacklist:
            if i in str(member.name).lower():
                await member.kick(reason="clonex")


def setup(bot):
    bot.add_cog(Antiraid(bot))
