import logging
import asyncio
from datetime import datetime, timedelta, timezone
import numpy as np
import json

import discord
from discord.ext import commands

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

        for giveaway in self.giveaway_db.find():
            if giveaway["giveaway_over"] == False:
                self.active_giveaways[giveaway["pin"]] = giveaway
                time = giveaway["end_time"] - datetime.utcnow().timestamp()
                if time < 0:
                    time = 1
                giveaway_task = asyncio.create_task(
                    self.start_giveaway(giveaway), name=giveaway["pin"]
                )
                await giveaway_task

    @commands.group(hidden=True)
    async def giveaway(self, ctx):
        """
        giveaway commands
        Usage: giveaway start/end/cancel/reroll/list
        """

    async def choose_winner(self, giveaway):
        """does the giveaway logic"""

        try:
            channel = await self.bot.fetch_channel(giveaway["channel_id"])
            message = await channel.fetch_message(giveaway["message_id"])

            embed = message.embeds[0].to_dict()

            embed["title"] = "Giveaway ended"
            embed["color"] = 15158332  # red
            embed["footer"]["text"] = "Giveaway Ended"

            users = []

            for reaction in message.reactions:
                if reaction.emoji == "🎉":
                    users = await reaction.users().flatten()
                    userids = [user.id for user in users if user.id != self.bot.user.id]
                    users = []
                    for userid in userids:
                        try:
                            member = await message.guild.fetch_member(userid)
                            users.append(member)
                        except discord.errors.NotFound:
                            pass

            if users != []:
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

                choice = np.random.choice(users, size=size, replace=False, p=prob)
                winners = []
                winnerids = ", ".join([str(i.id) for i in choice])
                for winner in choice:
                    await message.channel.send(
                        f"{winner.mention} won **{giveaway['prize']}**!"
                    )
                    winners.append(f"> {winner.mention}")
                winners = "\n".join(winners)

            else:
                winners = "> Nobody participated :("
                winnerids = ""

            newdescription = embed["description"].splitlines()
            for i in range(len(newdescription)):
                if newdescription[i].startswith("> **Winners"):
                    newdescription.insert(i + 1, winners)
                    break

            embed["description"] = "\n".join(newdescription)

            embed = discord.Embed.from_dict(embed)
            await message.edit(embed=embed)

        except discord.errors.NotFound:
            del self.active_giveaways[giveaway["pin"]]
            self.giveaway_db.update_one(
                giveaway, {"$set": {"giveaway_cancelled": True}}
            )
            pass

        if giveaway["pin"] in self.active_giveaways:
            del self.active_giveaways[giveaway["pin"]]
            self.giveaway_db.update_one(
                giveaway,
                {"$set": {"giveaway_over": True, "winners": winnerids}},
            )
        else:
            winnerids += f", old: {giveaway['winners']}"
            self.giveaway_db.update_one(giveaway, {"$set": {"winners": winnerids}})

    async def start_giveaway(self, giveaway):
        """Sets up a giveaway task"""
        time = giveaway["end_time"] - datetime.utcnow().timestamp()
        await asyncio.sleep(time)
        await self.choose_winner(giveaway)

    @mod_and_above()
    @giveaway.command()
    async def start(self, ctx, time, *, giveaway_msg):
        """Starts a new giveaway
        Usage: giveaway start time (dash arguments) prize \n dash args: -w no_of_winners -s sponsor -r rigged"""

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
                try:
                    winners = int(a[1])
                except:
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
            arguments.remove(a[0])
            arguments.remove(a[1])

        giveaway_msg = " ".join(arguments)

        if time is None:
            raise commands.BadArgument(message="Wrong time syntax")

        embed = discord.Embed(
            title="Giveaway started!",
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=time),
            colour=discord.Colour.green(),
        )
        description = f"**{giveaway_msg}\n**"
        for field in fields:
            description += "\n" + fields[field]

        embed.description = description

        uid = str(datetime.utcnow().timestamp())[-3:] + "0"
        c = 0
        while uid in self.active_giveaways:
            c += 1
            uid = uid[:3] + str(c)

        embed.set_footer(text=f"PIN: {uid} | Giveaway Ends")

        message = await ctx.send(embed=embed)
        await message.add_reaction("🎉")

        doc = {
            "pin": uid,
            "prize": giveaway_msg,
            "end_time": datetime.utcnow().timestamp() + time,
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

        giveaway = asyncio.create_task(self.start_giveaway(doc), name=uid)

        self.active_giveaways[uid] = doc
        self.giveaway_db.insert_one(doc)

        await giveaway

    @mod_and_above()
    @giveaway.command()
    async def end(self, ctx, pin: str):
        """Ends the giveaway early
        Usage: giveaway end pin"""

        if pin in self.active_giveaways:
            await self.choose_winner(self.active_giveaways[pin])

            for i in asyncio.all_tasks():
                if i.get_name() == pin:
                    i.cancel()
                    break
        else:
            await ctx.send("Giveaway not found!", delete_after=6)
            await ctx.message.delete(delay=6)

    @mod_and_above()
    @giveaway.command()
    async def cancel(self, ctx, pin: str):
        """Cancel a giveaway
        Usage: giveaway cancel pin"""
        if pin in self.active_giveaways:
            giveaway = self.active_giveaways[pin]
            message = await ctx.guild.get_channel(giveaway["channel_id"]).fetch_message(
                giveaway["message_id"]
            )
            await message.delete()
            del self.active_giveaways[pin]
            self.giveaway_db.update_one(
                giveaway, {"$set": {"giveaway_cancelled": True}}
            )

            for i in asyncio.all_tasks():
                if i.get_name() == pin:
                    i.cancel()
                    break

            await ctx.send("Giveaway cancelled!", delete_after=6)
        else:
            await ctx.send("Giveaway not found!", delete_after=6)
            await ctx.message.delete(delay=6)

    @mod_and_above()
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

        for i in self.giveaway_db.find():
            if i["message_id"] == giveaway:
                doc = i
                if winners != None:
                    doc["winners_no"] = winners
                if rigged != None:
                    doc["rigged"] = rigged
                await self.choose_winner(doc)
                return
        await ctx.send("Giveaway not found!", delete_after=6)

    @mod_and_above()
    @giveaway.command()
    async def list(self, ctx):
        """Lists all active giveaways
        Usage: giveaway list"""
        giveaways = []
        for i in self.active_giveaways:
            i = self.active_giveaways[i]
            msg = f'{i["prize"]} | {round((i["end_time"] - datetime.utcnow().timestamp())/60)}min left | PIN: {i["pin"]}'
            giveaways.append(msg)

        giveaways = "\n".join(giveaways)
        embed = discord.Embed(title="Active giveaways:", description=giveaways)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Giveaway(bot))
