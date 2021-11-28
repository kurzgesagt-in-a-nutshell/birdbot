import logging
import asyncio
from datetime import datetime, timedelta, timezone
import numpy as np
import json

import discord
from discord.ext import commands
from utils.helper import calc_time
from utils.custom_converters import member_converter

import typing


class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Giveaway")
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Giveaway")

        with open("config.json", "r") as config_file:
            config_json = json.loads(config_file.read())

        self.giveaway_tasks = []

        self.giveaway_bias = config_json["giveaway"]

        self.active_giveaways = []

        self.giveaway_db = self.bot.db.Giveaways

        for giveaway in self.giveaway_db.find():
            if giveaway["giveaway_over"] == False:
                self.active_giveaways.append(giveaway)
                time = giveaway["end_time"] - datetime.utcnow().timestamp()
                if time < 0:
                    time = 1
                giveaway_task = asyncio.create_task(self.start_giveaway(giveaway))
                self.giveaway_tasks.append((giveaway["message_id"], giveaway_task))
                await giveaway_task

    @commands.group(hidden=True)
    async def giveaway(self, ctx: commands.Context):
        """
        giveaway commands
        Usage: giveaway < start | end | cancel | reroll | list>
        """

    async def choose_winner(self, giveaway):
        """does the giveaway logic"""

        channel = await self.bot.fetch_channel(giveaway["channel_id"])
        message = await channel.fetch_message(giveaway["message_id"])

        embed = message.embeds[0].to_dict()

        embed["title"] = "GiveAway ended"
        embed["color"] = 15158332  # red
        embed["footer"]["text"] = "GiveAway Ended"

        for reaction in message.reactions:
            if reaction.emoji == "🎉":
                users = await reaction.users().flatten()
                users = [user.id for user in users]
                users.remove(self.bot.user.id)

        if users != []:
            weights = []
            for user in users:
                bias = self.giveaway_bias["default"]
                member = await message.guild.fetch_member(user)
                roles = [role.id for role in member.roles]
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
            winners = ""
            for i in choice:
                winner = await message.guild.fetch_member(i)
                await message.channel.send(f"{winner.mention} won")
                winners += winner.mention + "\n"
        else:
            winners = "Nobody participated :("

        for i in embed["fields"]:
            if i["name"].startswith("winners"):
                i["value"] = winners

        embed = discord.Embed.from_dict(embed)
        await message.edit(embed=embed)

        if giveaway in self.active_giveaways:
            self.active_giveaways.remove(giveaway)

            self.giveaway_db.update_one(giveaway, {"$set": {"giveaway_over": True}})

        for i in self.giveaway_tasks:
            if i[0] == message.id:
                self.giveaway_tasks.remove(i)
                break

    async def start_giveaway(self, giveaway):
        """Sets up a giveaway task"""
        time = giveaway["end_time"] - datetime.utcnow().timestamp()
        await asyncio.sleep(time)
        await self.choose_winner(giveaway)

    @giveaway.command()
    async def start(self, ctx, time, *, giveaway_msg):
        """Starts a new giveaway
        Usage: giveaway start time (dash arguments) prize \n dash args: -w no_of_winners -s sponsor -r rigged"""

        time, giveaway_msg = calc_time([time, giveaway_msg])
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
            "winners": {"name": "winners: 1", "value": " ​"},
            "sponsor": {"name": "hosted by", "value": ctx.author.mention},
        }

        for a in dash_args:
            if a[0] == "-w":
                fields["winners"] = {"name": f"winners: {a[1]}", "value": " ​"}
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
                fields["sponsor"] = {"name": "sponsored by", "value": sponsor}
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
            title="GiveAway started!",
            description=f"**{giveaway_msg}**",
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=time),
            colour=discord.Colour.green(),
        )
        for field in fields:
            embed.add_field(
                name=fields[field]["name"], value=fields[field]["value"], inline=False
            )

        uid = str(datetime.utcnow().timestamp())[-3:]
        c = 0
        for i in self.active_giveaways:
            if list(i)[:3] == uid:
                c += 1
        uid += str(c)

        embed.set_footer(text=f"PIN: {uid} | GiveAway Ends")

        message = await ctx.send(embed=embed)
        await message.add_reaction("🎉")

        doc = {
            "pin": uid,
            "prize": giveaway_msg,
            "end_time": datetime.utcnow().timestamp() + time,
            "message_id": message.id,
            "channel_id": message.channel.id,
            "winners_no": winners,
            "rigged": rigged,
            "host": ctx.author.id,
            "sponsor": sponsor,
            "giveaway_over": False,
        }

        giveaway = asyncio.create_task(self.start_giveaway(doc))

        self.active_giveaways.append(doc)
        self.giveaway_db.insert_one(doc)
        self.giveaway_tasks.append((message.id, giveaway))

        await giveaway

    @giveaway.command()
    async def end(self, ctx, giveaway: str):
        """Ends the giveaway early
        Usage: giveaway end pin"""
        for i in self.active_giveaways:
            if i["pin"] == giveaway:
                message_id = i["message_id"]
                await self.choose_winner(i)
                break
        for i in self.giveaway_tasks:
            if i[0] == message_id:
                i[1].cancel()
                self.giveaway_tasks.remove(i)
                break

    @giveaway.command()
    async def cancel(self, ctx, giveaway: str):
        """Deletes a giveaway
        Usage: giveaway delete pin"""
        for i in self.active_giveaways:
            if i["pin"] == giveaway:
                message = await ctx.guild.get_channel(i["channel_id"]).fetch_message(
                    i["message_id"]
                )
                await message.delete()
                self.active_giveaways.remove(i)
                self.giveaway_db.delete_one(i)
                break
        for i in self.giveaway_tasks:
            if i[0] == message.id:
                i[1].cancel()
                self.giveaway_tasks.remove(i)
                break

        await ctx.send("Giveaway cancelled", delete_after=6)

    @giveaway.command()
    async def reroll(
        self,
        ctx,
        giveaway: int,
        winners: typing.Optional[int] = None,
        rigged: typing.Optional[bool] = None,
    ):
        """Pick a new winner"""
        for i in self.giveaway_db.find():
            if i["message_id"] == giveaway:
                doc = i
                if winners != None:
                    doc["winners_no"] = winners
                if rigged != None:
                    doc["rigged"] = rigged
                await self.choose_winner(doc)

    @giveaway.command()
    async def list(self, ctx):
        """Lists all active giveaways
        Usage: giveaway list"""
        giveaways = []
        for i in self.active_giveaways:
            msg = f'{i["prize"]} | {round(i["end_time"] - datetime.utcnow().timestamp())}s left | PIN: {i["pin"]}'
            giveaways.append(msg)

        giveaways = "\n".join(giveaways)
        embed = discord.Embed(title="Active giveaways:", description=giveaways)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Giveaway(bot))
