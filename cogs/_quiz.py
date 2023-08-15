import logging
import numpy as np
import os
import asyncio
from utils.helper import admin_and_above

import pymongo
from discord.ext import commands

from utils.config import Reference


class Quiz(commands.Cog):
    db_qz_key = os.environ.get("DB_QZ_KEY")
    qclient = pymongo.MongoClient(db_qz_key)
    qdb = qclient.QZ
    quiz_db = qdb.AndrewQuiz
    id_and_tickets = []

    def __init__(self, bot):
        self.logger = logging.getLogger("Quiz")
        self.bot = bot
        self.id_and_tickets = list(
            self.quiz_db.find({"tickets": {"$ne": 0}}, {"id": 1, "tickets": 1})
        )

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Quiz")

    @commands.command()
    async def tickets(self, ctx):
        if ctx.channel.id != Reference.Channels.bot_commands:
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
    async def end(self, ctx, winners, *, prize):
        """end giveaway"""
        role_boosts = {
            821961644425871390: 0.01,
            637114722675851302: 0.02,
            637114849570062347: 0.04,
            637114873268142081: 0.06,
            637114897544511488: 0.08,
            637114917178048543: 0.10,
            662937489220173884: 0.12,
            698479120878665729: 0.15,
        }

        async def process_users():
            """remove users not in server and add ticket boost"""
            kgs_guild = self.bot.get_guild(Reference.guild)

            for i in self.id_and_tickets:
                user = kgs_guild.get_member(int(i["id"]))
                if user is None:
                    self.id_and_tickets.remove(i)
                    continue

                # check if user has any leveled roles
                to_boost = [
                    role
                    for role in list(role_boosts.keys())
                    if role in [user_role.id for user_role in user.roles]
                ]
                if len(to_boost) != 0:
                    self.logger.info(
                        f"boosting {user.name} for having role {to_boost[0]} by {role_boosts[to_boost[0]]}"
                    )
                    i["tickets"] += round(i["tickets"] * role_boosts[to_boost[0]])

        await process_users()

        async with ctx.channel.typing():

            tickets = [x["tickets"] for x in self.id_and_tickets]
            total = sum(tickets)
            probability = []

            for i in tickets:
                probability.append(i / total)

            rng = np.random.default_rng()
            winner = rng.choice(
                self.id_and_tickets, size=int(winners), replace=False, p=probability
            )
            self.logger.info(winner)
            # await asyncio.sleep(4)
            await ctx.send(
                f'**And the winner for {prize} {"is" if int(winners) == 1 else "are "}...**'
            )
            await asyncio.sleep(3)
            for i in winner:

                await asyncio.sleep(3)
                await ctx.send(
                    f"<@{i['id']}> - {i['tickets']} tickets ({round((i['tickets']/total)*100,3)}% chance of winning)"
                )
                self.id_and_tickets.remove(i)


async def setup(bot):
    await bot.add_cog(Quiz(bot))
