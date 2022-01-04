import logging
import os

import discord
import pymongo
from discord.ext import commands


class Quiz(commands.Cog):
    db_qz_key = os.environ.get('DB_QZ_KEY')
    qclient = pymongo.MongoClient(db_qz_key)
    qdb = qclient.QZ
    quiz_db = qdb.AndrewQuiz

    def __init__(self, bot):
        self.logger = logging.getLogger('Quiz')
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Quiz')

    @commands.command()
    async def tickets(self, ctx):
        if ctx.channel != 414452106129571842:
            return;
        try:
            user = self.quiz_db.find_one({"id": str(ctx.author.id)})
            if user:
                pipe = [{'$group': {"_id": None, 'total': {'$sum': '$tickets'}}}]
                total_tickets = list(self.quiz_db.aggregate(pipeline=pipe))[0]["total"]
                percentage = round((user["tickets"] / total_tickets) * 100, 3)

                await ctx.send(f'You have {user["tickets"]} tickets of { total_tickets } tickets ( {percentage}% chance of winning ).')
            else:
                await ctx.send(f"You have not participated. To participate please vist `https://quiz.birdbot.xyz`")

        except Exception as e:
            logging.error(str(e))


def setup(bot):
    bot.add_cog(Quiz(bot))
