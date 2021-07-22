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

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Fun')

    @commands.command()
    @commands.cooldown(1, 60)
    async def topic(self, ctx):
        """Get a topic to talk about."""
        random_index = random.randint(0, len(self.topics))
        await ctx.send(f'{random_index + 1}. {self.topics[random_index]}')

    @commands.command()
    @mod_and_above()
    async def get_topic(self, ctx, index: int):
        """
            Get a topic by index.
            Usage: get_topic index
        """
        if index < 1 or index > len(self.topics):
            await ctx.send(f'Invalid index. Min value: 0, Max value: {len(self.topics)}', delete_after=6)
            return await ctx.message.delete(delay=4)

        await ctx.send(f'{index}. {self.topics[index - 1]}', delete_after=6)
        await ctx.message.delete(delay=4)

    @commands.command(hidden=True)
    @mod_and_above()
    async def remove_topic(self, ctx, index: int):
        """
            Delete topic by index.
            Usage: remove_topic index
        """
        if index < 1 or index > len(self.topics):
            await ctx.send(f'Invalid index. Min value: 0, Max value: {len(self.topics)}', delete_after=6)
            return await ctx.message.delete(delay=4)

        index = index - 1

        topic_file = open('topics.json', 'r')
        topics = json.loads(topic_file.read())["topics"]
        topic_file.close()

        del topics[index]

        self.topics = topics

        topic_file = open('topics.json', 'w')
        topic_file.write(json.dumps({"topics": topics}, indent=4))
        topic_file.close()
        await ctx.send('Topic removed.', delete_after=6)
        await ctx.message.delete(delay=4)

    @commands.command()
    @mod_and_above()
    async def add_topic(self, ctx, topic: str):
        """
            Add a topic to the list.
            Usage: add_topic topic_string
        """
        topic_file = open('topics.json', 'r')
        topics = json.loads(topic_file.read())["topics"]
        topic_file.close()

        topics.append(topic)

        self.topics = topics

        topic_file = open('topics.json', 'w')
        topic_file.write(json.dumps({"topics": topics}, indent=4))
        topic_file.close()

        await ctx.send(f'Topic added at index {len(self.topics)}', delete_after=6)
        await ctx.message.delete(delay=4)


def setup(bot):
    bot.add_cog(Fun(bot))
