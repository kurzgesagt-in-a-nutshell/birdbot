import logging
import os
import json
import random

import discord
from discord.ext import commands

from helper import mod_and_above


class Fun(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Fun')
        self.bot = bot

        topic_file = open('topics.json', 'r')

        self.topics = json.loads(topic_file.read())["topics"]

        topic_file.close()

    @ commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Fun')

    @ commands.command()
    @ commands.cooldown(1, 30)
    async def topic(self, ctx):
        """Command description"""
        try:
            random_index = random.randint(0, len(self.topics))
            await ctx.send(self.topics[random_index])

        except Exception as e:
            self.logger.error(str(e))


def setup(bot):
    bot.add_cog(Fun(bot))
