import logging
import asyncio
from datetime import datetime, timedelta, timezone
import numpy as np
import json

import discord
from discord.ext import commands, tasks

from utils.helper import (
    calc_time,
    devs_only,
    mod_and_above,
)
from utils.custom_converters import member_converter

import typing


class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Giveaway")
        self.bot = bot
        with open("config.json", "r") as config_file:
            config_json = json.loads(config_file.read())
        self.giveaway_bias = config_json["giveaway"]
        self.active_giveaways = {}
        self.giveaway_db = self.bot.db.Giveaways

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Giveaway")

        for giveaway in self.giveaway_db.find({"giveaway_over": False, "giveaway_cancelled": False}):
            self.active_giveaways[giveaway["message_id"]] = giveaway

        self.giveaway_task.start()

    def cog_unload(self):
        self.giveaway_task.cancel()

    @mod_and_above()
    @commands.group(hidden=True)
    async def giveaway(self, ctx):
        """
        giveaway commands
        Usage: giveaway start/end/cancel/reroll/list
        """

    async def choose_winner(self, giveaway):
        """does the giveaway logic"""
        messagefound = False
        try:
            channel = await self.bot.fetch_channel(giveaway["channel_id"])
            message = await channel.fetch_message(giveaway["message_id"])
            messagefound = True
        except:
            messagefound = False

        if messagefound:
            if message.author != self.bot.user:
                if giveaway["message_id"] in self.active_giveaways:
                    del self.active_giveaways[giveaway["message_id"]]
                return

            embed = message.embeds[0].to_dict()

            embed["title"] = "Giveaway ended"
            embed["color"] = 15158332  # red
            embed["footer"]["text"] = "Giveaway Ended"

            users = []
            self.logger.debug("Fetching reactions from users")
            for reaction in message.reactions:
                if reaction.emoji == "🎉":
                    userids = [
                        user.id
                        async for user in reaction.users()
                        if user.id != self.bot.user.id
                    ]
                    users = []
                    for userid in userids:
                        try:
                            member = await message.guild.fetch_member(userid)
                            users.append(member)
                        except discord.errors.NotFound:
                            pass

            self.logger.debug("Fetched users")

            if users != []:
                self.logger.debug("Calculating weights")
                weights = []
                for user in users:
                    bias = self.giveaway_bias["default"]
                    roles = [role.id for role in user.roles]
                    for role in self.giveaway_bias["roles"]:
                        if role["id"] in roles:
                            bias = role["bias"]
                            break
                    weights.append(bias)

                total = sum(weights)
                probabilities = [w / total for w in weights]
                prob = np.array(probabilities)

                if giveaway["rigged"] == False:
                    prob = None

                size = giveaway["winners_no"]
                if len(users) < size:
                    size = len(users)

                self.logger.debug("Choosing winner(s)")
                choice = np.random.choice(users, size=size, replace=False, p=prob)
                winners = []
                winnerids = ", ".join([str(i.id) for i in choice])
                self.logger.debug(f"Fetched winner(s): {winnerids}")
                for winner in choice:
                    await message.reply(
                        f"{winner.mention} won **{giveaway['prize']}**!"
                    )
                    winners.append(f"> {winner.mention}")
                winners = "\n".join(winners)

            else:
                winners = "> Nobody participated :("
                winnerids = ""

            self.logger.debug("Sending new embed")
            newdescription = embed["description"].splitlines()
            for i in range(len(newdescription)):
                if newdescription[i].startswith("> **Winners"):
                    newdescription.insert(i + 1, winners)
                    break

            embed["description"] = "\n".join(newdescription)

            embed = discord.Embed.from_dict(embed)
            await message.edit(embed=embed)

        else:
            self.logger.debug("Message not found")
            self.logger.debug("Deleting giveaway")
            del self.active_giveaways[giveaway["message_id"]]
            self.giveaway_db.update_one(
                giveaway, {"$set": {"giveaway_cancelled": True}}
            )
            return

        if giveaway["message_id"] in self.active_giveaways:
            self.logger.debug("Deleting giveaway")
            del self.active_giveaways[giveaway["message_id"]]
            self.giveaway_db.update_one(
                giveaway,
                {"$set": {"giveaway_over": True, "winners": winnerids}},
            )
        else:
            self.logger.debug("Appending old winners and updating giveaway")
            winnerids += f", old: {giveaway['winners']}"
            self.giveaway_db.update_one(giveaway, {"$set": {"winners": winnerids}})

    @tasks.loop()
    async def giveaway_task(self):
        templist = list(self.active_giveaways)
        firstgiveaway = {}

        self.logger.debug("Checking for giveaways")
        self.logger.debug(f"{len(templist)} giveaways found: {templist}")
        for i in templist:
            giveaway = self.active_giveaways[i]
            if giveaway["end_time"] - datetime.utcnow() <= timedelta():
                await self.choose_winner(giveaway)
            else:
                if not firstgiveaway:
                    firstgiveaway = giveaway
                if giveaway["end_time"] < firstgiveaway["end_time"]:
                    firstgiveaway = giveaway

        self.logger.debug(f"Checking for first giveaway, {firstgiveaway}")
        if firstgiveaway:
            self.logger.debug(f"Sleeping for: {firstgiveaway['end_time']}")
            await discord.utils.sleep_until(firstgiveaway["end_time"])
            self.logger.debug(f"Choosing winner for {firstgiveaway}")
            await self.choose_winner(firstgiveaway)
        else:
            self.giveaway_task.cancel()

    @giveaway.command()
    async def start(self, ctx, time, *, giveaway_msg):
        """Starts a new giveaway
        Usage: giveaway start time (dash arguments) prize \n dash args: -w no_of_winners -s sponsor -r rigged
        default values for dash arguments: -w 1 -s host -r y"""

        time, giveaway_msg = calc_time([time, giveaway_msg])
        if time == 0:
            raise commands.BadArgument(message="Time can't be 0")
        winners = 1
        rigged = True
        sponsor = ctx.author.id
        if giveaway_msg == None:
            raise commands.BadArgument(
                message="Calculating time went wrong (did you follow it up with a number?)"
            )
        arguments = giveaway_msg.split(" ")
        dash_args = []

        for i in range(len(arguments) - 1):
            if arguments[i].startswith("-"):
                dash_args.append([arguments[i], arguments[i + 1]])

        fields = {
            "winners": "> **Winners: 1**",
            "sponsor": f"> **Hosted by**\n> {ctx.author.mention}",
        }

        for a in dash_args:
            if a[0] == "-w":
                fields["winners"] = f"> **Winners: {a[1]}**"
                if a[1].isdigit():
                    winners = int(a[1])
                else:
                    raise commands.BadArgument(
                        message="No of winners must be an integer"
                    )
            elif a[0] == "-s":
                try:
                    sponsor = member_converter(ctx, a[1]).mention
                except:
                    raise commands.BadArgument(message="Improper mention of user")
                fields["sponsor"] = f"> **Sponsored by**\n> {sponsor}"
                sponsor = member_converter(ctx, a[1]).id
            elif a[0] == "-r":
                if a[1].lower() == "y" or a[1].lower() == "yes":
                    rigged = True
                elif a[1].lower() == "n" or a[1].lower() == "no":
                    rigged = False
                else:
                    raise commands.BadArgument(message="Argument must be y/n")
            if a[0] in ["-w", "-s", "-r"]:
                arg = " ".join(a)
                if arg + " " in giveaway_msg:
                    giveaway_msg = giveaway_msg.replace(arg + " ", "")
                else:
                    giveaway_msg = giveaway_msg.replace(arg, "")

        if time is None:
            raise commands.BadArgument(message="Wrong time syntax")

        time = datetime.utcnow() + timedelta(seconds=time)

        embed = discord.Embed(
            title="Giveaway started!",
            timestamp=time,
            colour=discord.Colour.green(),
        )
        riggedinfo = ""
        if rigged:
            riggedinfo = "[rigged](https://discord.com/channels/414027124836532234/414452106129571842/714496884844134401)"

        description = (
            f"**{giveaway_msg}**\nReact with 🎉 to join the {riggedinfo} giveaway\n"
        )
        for field in fields:
            description += "\n" + fields[field]

        embed.description = description

        embed.set_footer(text="Giveaway Ends")

        message = await ctx.send(embed=embed)
        await message.add_reaction("🎉")

        doc = {
            "prize": giveaway_msg,
            "end_time": time,
            "message_id": message.id,
            "channel_id": message.channel.id,
            "winners_no": winners,
            "winners": "",
            "rigged": rigged,
            "host": ctx.author.id,
            "sponsor": sponsor,
            "giveaway_over": False,
            "giveaway_cancelled": False,
        }

        self.active_giveaways[doc["message_id"]] = doc

        self.giveaway_db.insert_one(doc)

        if self.giveaway_task.is_running():
            self.giveaway_task.restart()
        else:
            self.giveaway_task.start()

        await ctx.message.add_reaction("<:kgsYes:955703069516128307>")

    @giveaway.command()
    async def end(self, ctx, messageid: int):
        """Ends the giveaway early
        Usage: giveaway end messageid"""

        if messageid in self.active_giveaways:
            await self.choose_winner(self.active_giveaways[messageid])
            self.giveaway_task.restart()
            await ctx.message.add_reaction("<:kgsYes:955703069516128307>")
            return

        await ctx.send("Giveaway not found!", delete_after=6)
        await ctx.message.delete(delay=6)

    @giveaway.command()
    async def cancel(self, ctx, messageid: int):
        """Cancel a giveaway
        Usage: giveaway cancel messageid"""

        if messageid in self.active_giveaways:
            giveaway = self.active_giveaways[messageid]

            try:
                message = await ctx.guild.get_channel(
                    giveaway["channel_id"]
                ).fetch_message(giveaway["message_id"])
                await message.delete()
            except:
                pass

            del self.active_giveaways[messageid]
            self.giveaway_task.restart()
            self.giveaway_db.update_one(
                giveaway, {"$set": {"giveaway_cancelled": True}}
            )
            await ctx.send("Giveaway cancelled!", delete_after=6)
            await ctx.message.add_reaction("<:kgsYes:955703069516128307>")
            return

        await ctx.send("Giveaway not found!", delete_after=6)
        await ctx.message.delete(delay=6)

    @giveaway.command()
    async def reroll(
        self,
        ctx,
        giveaway: int,
        winners: typing.Optional[int] = None,
        rigged: typing.Optional[str] = None,
    ):
        """Pick a new winner
        Usage: giveaway reroll messageid <no_of_winners> <rigged>"""
        if rigged != None:
            if rigged.lower() == "y" or rigged.lower() == "yes":
                rigged = True
            elif rigged.lower() == "n" or rigged.lower() == "no":
                rigged = False
            else:
                raise commands.BadArgument(message="Rigged argument must be y/n")

        doc = self.giveaway_db.find_one({"giveaway_over": True, "message_id": giveaway})
        if doc:
            if winners != None:
                doc["winners_no"] = winners
            if rigged != None:
                doc["rigged"] = rigged
            await self.choose_winner(doc)
            await ctx.message.add_reaction("<:kgsYes:955703069516128307>")
            return

        await ctx.send("Giveaway not found!", delete_after=6)
        await ctx.message.delete(delay=6)

    @giveaway.command()
    async def list(self, ctx):
        """Lists all active giveaways
        Usage: giveaway list"""
        embed = discord.Embed(title="Active giveaways:")
        for messageid in self.active_giveaways:
            giveaway = self.active_giveaways[messageid]
            try:
                time = giveaway["end_time"] - datetime.utcnow()
                embed.add_field(
                    name=giveaway["prize"],
                    value=f"[Giveaway](https://discord.com/channels/414027124836532234/{giveaway['channel_id']}/{giveaway['message_id']}) ends in {int(time.total_seconds()/60)} minutes",
                )
            except:
                pass

        await ctx.send(embed=embed)
        await ctx.message.add_reaction("<:kgsYes:955703069516128307>")


async def setup(bot):
    await bot.add_cog(Giveaway(bot))
