import logging
import numpy as np
import os
from utils import app_checks

import pymongo
import discord
from discord.ext import commands
from discord import ui, app_commands



class VideoQuiz(commands.Cog):


    def __init__(self, bot) -> None:
        self.logger = logging.getLogger("Spot The Scene")
        self.bot = bot
        self.db_qz_key = os.environ.get("DB_QZ_KEY")
        self.qclient = pymongo.MongoClient(self.db_qz_key)
        self.qdb = self.qclient.QZ
        self.quiz_db = self.qdb.SpotScene

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Spot The Scene")

    @app_commands.command()
    @app_commands.guilds(414027124836532234)
    @app_checks.mod_and_above()
    async def add_q(self,
                    interaction: discord.Interaction,
                    image: discord.Attachment,
                    answer: str
                    ):
        """Add a question for the upcoming quiz

        Parameters
        ----------
        image: discord.Attachment
            The image which the user has to find the timetamp for
        answer: str
            The timetamp URL (eg: https://youtu.be/dQw4w9WgXcQ?t=29) 
        """

        await interaction.response.defer(thinking=True)
        bot_testing = interaction.guild.get_channel(414179142020366336)
        f = await image.to_file()
        msg = await bot_testing.send(file=f)
        self.quiz_db.insert_one({"user_id":interaction.user.id,
                            "url":msg.attachments[0].url,
                            "answer":answer})
        return await interaction.edit_original_response(content="Done!")

async def setup(bot):
    await bot.add_cog(VideoQuiz(bot))