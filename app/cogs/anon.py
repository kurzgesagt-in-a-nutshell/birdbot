import logging
import typing
import numpy as np
import os
from app.utils import checks

import pymongo
import discord
from discord.ext import commands
from discord import ui, app_commands

from app.utils.config import Reference

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
    @app_commands.guilds(Reference.guild)
    @checks.mod_and_above()
    async def add_q(self,
                    interaction: discord.Interaction,
                    image: discord.Attachment,
                    answer: str,
                    difficulty: typing.Literal["Easy","Medium","Hard"]
                    ):
        """Add a question for the upcoming quiz

        Parameters
        ----------
        image: discord.Attachment
            The image which the user has to find the timetamp for
        answer: str
            The timetamp URL (eg: https://youtu.be/dQw4w9WgXcQ?t=29)
        difficulty: str
            How hard is this question? Must be "Easy", "Medium" or "Hard" 
        """

        await interaction.response.defer(thinking=True)
        bot_testing = interaction.guild.get_channel(Reference.Channels.bot_tests)
        f = await image.to_file()
        msg = await bot_testing.send(file=f)
        self.quiz_db.insert_one({"user_id":interaction.user.id,
                            "url":msg.attachments[0].url,
                            "answer":answer,
                            "difficulty":difficulty})
        return await interaction.edit_original_response(content="Done!")

async def setup(bot):
    await bot.add_cog(VideoQuiz(bot))