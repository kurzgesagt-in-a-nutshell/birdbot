import logging
import asyncio
from time import time as gettime
import numpy as np
import json

import discord
from discord.ext import commands
from utils.helper import calc_time
from utils.custom_converters import member_converter


class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Giveaway')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Giveaway')

        with open("config.json", "r") as config_file:
            config_json = json.loads(config_file.read())

        self.giveaway_tasks = {}

        self.giveaway_bias = config_json["giveaway"]

        self.active_giveaways = {} #get from mongodb

        #self.active_giveaways = self.bot.db.Giveaways

        for active_giveaway in self.active_giveaways:
            time = active_giveaway["time"] - gettime()
            if time < 0:
                time = 1
            giveaway = asyncio.create_task(self.start_giveaway(time, active_giveaway["message"], active_giveaway["winners"]))
            self.active_giveaways.append(giveaway)
            await giveaway

    @commands.group(hidden=True)
    async def giveaway(self, ctx: commands.Context):
        """
        giveaway commands
        Usage: giveaway < start | end | cancel | reroll | list>
        """

    async def choose_winner(self, message, winners):

        message = await message.channel.fetch_message(message.id)
        old_embed = message.embeds[0]

        embed = discord.Embed(title="Giveaway ended", description=old_embed.description)
        for i in old_embed.fields:
            if i.name == "sponsored by":
                embed.add_field(name=i.name, value=i.value, inline=False)

        for reaction in message.reactions:
            if reaction.emoji == '🎉':
                users = await reaction.users().flatten()
                users = [user.id for user in users]
                users.remove(self.bot.user.id)

        if users == []:
            await message.channel.send("No participants")
            embed.add_field(name="winners:", value="nobody participated :(", inline=False)
            await message.edit(embed=embed)
            return

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
        probabilities = [w/total for w in weights]
        prob = np.array(probabilities)

        choice = np.random.choice(users, size=winners, replace=True, p=prob)
        winners = ""
        for i in choice:
            winner = await message.guild.fetch_member(i)
            await message.channel.send(f'{winner.mention} won')
            winners += winner.mention + "\n"
        embed.add_field(name="winners:", value=winners, inline=False)
        await message.edit(embed=embed)

        if message.id in self.active_giveaways:
            del self.active_giveaways[message.id]
            del self.giveaway_tasks[message.id]

    async def start_giveaway(self, time, message, winners):
        """Sets up giveaway task to finish it"""
        await asyncio.sleep(time)
        await self.choose_winner(message, winners)


    @giveaway.command()
    async def start(self, ctx, time, *, giveaway_msg):
        """Command description"""

        time, giveaway_msg = calc_time([time, giveaway_msg])
        winners = 1

        arguments = giveaway_msg.split(" ")
        dash_args = []

        for i in range(len(arguments)):
            if arguments[i].startswith("-"):
                dash_args.append([arguments[i], arguments[i+1]])

        fields = []

        for a in dash_args:
            if a[0] == "-w":
                fields.append({"name":f"winners: {a[1]}", "value":" ​"})
                winners = int(a[1])
            elif a[0] == "-s":
                sponsor = member_converter(ctx, a[1]).mention
                fields.append({"name":"sponsored by", "value": sponsor})

            arguments.remove(a[0])
            arguments.remove(a[1])

        giveaway_msg = " ".join(arguments)

        if time is None:
            raise commands.BadArgument(
                message="Wrong time syntax"
            )

        embed = discord.Embed(title="Giveaway started!", description=giveaway_msg)
        for field in fields:
            #embed.add_field(name=field, value=" ​")
            embed.add_field(name=field["name"], value=field["value"], inline=False)
        message = await ctx.send(embed=embed)
        await message.add_reaction('🎉')

        giveaway = asyncio.create_task(self.start_giveaway(time, message, winners))

        self.active_giveaways[message.id] = {"time":gettime() + time, "message": message, "winners": winners}
        self.giveaway_tasks[message.id] = giveaway

        await giveaway

    @giveaway.command()
    async def end(self, ctx, giveaway: int):
        """Ends the giveaway early"""
        if int(giveaway) in self.active_giveaways:
            self.giveaway_tasks[giveaway].cancel()
            message = await self.active_giveaways[giveaway]["message"].channel.fetch_message(giveaway)
            winners = self.active_giveaways[giveaway]["winners"]
            await self.choose_winner(message, winners)
        


    @giveaway.command()
    async def cancel(self, ctx, giveaway: int):
        """Deletes a giveaway"""
        if int(giveaway) in self.active_giveaways:
            self.giveaway_tasks[giveaway].cancel()
            message = await self.active_giveaways[giveaway]["message"].channel.fetch_message(giveaway)
            await message.delete()
            del self.active_giveaways[giveaway]

        await ctx.send("Giveaway cancelled", delete_after=6)


    @giveaway.command()
    async def reroll(self, ctx, giveaway, winners: int):
        """Pick a new winner, only works in the giveaway channel"""
        message = await ctx.channel.fetch_message(giveaway)
        await self.choose_winner(message, winners)

    @giveaway.command()
    async def list(self, ctx):
        """Lists all active giveaways"""
        giveaways = []
        for i in self.active_giveaways:
            msg = str(self.active_giveaways[i]["message"].embeds[0].description) + " in " + str(round(self.active_giveaways[i]["time"] - gettime())) + "s id:" + str(self.active_giveaways[i]["message"].id)
            giveaways.append(msg)

        giveaways = "\n".join(giveaways)
        embed = discord.Embed(title="Active giveaways:", description=giveaways)
        await ctx.send(embed=embed)

        

def setup(bot):
    bot.add_cog(Giveaway(bot))
