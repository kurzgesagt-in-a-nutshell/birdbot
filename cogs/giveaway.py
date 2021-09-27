import logging
import asyncio
from random import choice as choose_winner
import time

import discord
from discord.ext import commands
from utils.helper import calc_time


class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Giveaway')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Giveaway')

        self.active_giveaways = [] #get from mongodb

    async def bias(self, users, guild):
        """Adds bias to giveaway. Separate function for easier editing."""
        users_bias = []

        for user in users:
            bias = 1
            member = await guild.fetch_member(user)
            roles = [role.id for role in member.roles]
            if 698479120878665729 in roles:  #galacduck
                bias = 11
            elif 662937489220173884 in roles:  #legendary duck
                bias = 7
            elif 637114917178048543 in roles:  #super duck
                bias = 4
            elif 637114897544511488 in roles: #duck
                bias = 3
            elif 637114873268142081 in roles: #smol duck
                bias = 2
            users_bias += [user]*bias

        return users_bias


    async def start_giveaway(self, time, message):
        """Sets up giveaway task to finish it"""
        await asyncio.sleep(time)
        message = await message.channel.fetch_message(message.id)

        for reaction in message.reactions:
            if reaction.emoji == '🎉':
                users = await reaction.users().flatten()
                users = [user.id for user in users]
                users.remove(self.bot.user.id)

        guild = message.guild
        users_bias = await self.bias(users, guild)

        if users_bias == []:
            await message.channel.send("No participants")
        else:
            winner = await guild.fetch_member(choose_winner(users_bias))
            await message.channel.send(f'{winner.mention} won')


    @commands.command()
    async def giveaway(self, ctx, status, time, *, giveaway_msg):
        """Command description"""

        time, giveaway_msg = calc_time([time, giveaway_msg])

        if time is None:
            raise commands.BadArgument(
                message="Wrong time syntax"
            )

        if status == "start":
            message = await ctx.send(f'Giveaway started {giveaway_msg}')
            await message.add_reaction('🎉')
            
            giveaway = asyncio.create_task(self.start_giveaway(time, message))

            await giveaway
    

def setup(bot):
    bot.add_cog(Giveaway(bot))

