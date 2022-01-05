import logging
import pickle
import numpy as np
import os
import asyncio
from utils.helper import admin_and_above

import discord
import pymongo
from discord.ext import commands


class Quiz(commands.Cog):
    db_qz_key = os.environ.get("DB_QZ_KEY")
    qclient = pymongo.MongoClient(db_qz_key)
    qdb = qclient.QZ
    quiz_db = qdb.AndrewQuiz
    id_and_tickets = []

    def __init__(self, bot):
        self.logger = logging.getLogger("Quiz")
        self.bot = bot
        self.id_and_tickets = list(self.quiz_db.find({"tickets": {"$ne":0}}, {"id": 1, "tickets": 1}))

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Quiz")

    @commands.command()
    async def tickets(self, ctx):
        if ctx.channel.id != 414452106129571842:
            return
        try:
            user = self.quiz_db.find_one({"id": str(ctx.author.id)})
            if user:
                pipe = [{"$group": {"_id": None, "total": {"$sum": "$tickets"}}}]
                total_tickets = list(self.quiz_db.aggregate(pipeline=pipe))[0]["total"]
                percentage = round((user["tickets"] / total_tickets) * 100, 3)

                await ctx.send(
                    f'You have {user["tickets"]} tickets of { total_tickets } tickets ( {percentage}% chance of winning ).'
                )
            else:
                await ctx.send(
                    f"You have not participated. To participate please vist `https://quiz.birdbot.xyz`"
                )

        except Exception as e:
            logging.error(str(e))


    @admin_and_above()
    @commands.command(hidden=True)
    async def end(self, ctx, winners, *,prize):
        """end giveaway"""

        async def sanitize_users():
            """remove users not in server"""
            kgs_guild = self.bot.get_guild(414027124836532234)
            for i in self.id_and_tickets:
                if kgs_guild.get_member(int(i["id"])) is None:
                    self.id_and_tickets.remove(i)

        await sanitize_users()

        async with ctx.channel.typing():

            tickets = [x['tickets'] for x in self.id_and_tickets]
            total = sum(tickets)
            probability = []

            for i in tickets:
                probability.append(i/total)

            rng = np.random.default_rng()
            winner = rng.choice(
                self.id_and_tickets,size=int(winners), replace=False, p=probability)
            self.logger.info(winner)
            # await asyncio.sleep(4)
            await ctx.send(f'**And the winner for {prize} {"is" if int(winners) == 1 else "are "}...**')
            await asyncio.sleep(3)
            for i in winner:

                await asyncio.sleep(3)
                await ctx.send(f"<@{i['id']}> - {i['tickets']} tickets ({round((i['tickets']/total)*100,3)}% chance of winning)")
                self.id_and_tickets.remove(i)

def setup(bot):
    bot.add_cog(Quiz(bot))
