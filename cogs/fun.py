import logging
import os
import json
import random
from re import search
from fuzzywuzzy import process
import asyncio

import discord
from discord.ext import commands

from helper import mod_and_above


class Fun(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Fun')
        self.bot = bot

        topic_file = open('topics.json', 'r')

        self.topics = json.loads(topic_file.read())["topics"]
        self.topics_random = self.topics

        topic_file.close()
    	
        self.suggestion_msg_ids = []

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Fun')

    @commands.command()
    @commands.cooldown(1, 60)
    async def topic(self, ctx):
        """Get a topic to talk about."""
        if self.topics_random == []:
            self.topics_random = self.topics
        random_index = random.randint(0, len(self.topics_random)-1)
        await ctx.send(f'{self.topics_random.pop(random_index)}')


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

        await ctx.send(f'{index}. {self.topics[index - 1]}')

    @mod_and_above()
    @commands.command()
    @commands.cooldown(1, 5)
    async def add_topic(self, ctx, topic: str):
        """
            Add a topic to the list.
            Usage: add_topic topic_string
        """

        self.topics.append(topic)

        topic_file = open('topics.json', 'w')
        topic_file.write(json.dumps({"topics": self.topics}, indent=4))
        topic_file.close()

        await ctx.send(f'Topic added at index {len(self.topics)}', delete_after=6)
        await ctx.message.delete(delay=4)

    @commands.command()
    @commands.cooldown(1, 5)
    async def suggest_topic(self, ctx, topic: str):
        """
            Suggest a topic.
            Usage: suggest_topic topic_string
        """

        await ctx.send(f'Topic suggested.', delete_after=6)
        await ctx.message.delete(delay=4)

        automated_channel = self.bot.get_channel(414179142020366336)
        embed = discord.Embed(title=f'{ctx.author.name} suggested', description=topic, color=0xff0000)
        message = await automated_channel.send(embed=embed)
        self.suggestion_msg_ids.append(message.id)
        await message.add_reaction('<:kgsYes:580164400691019826>')
        await message.add_reaction('<:kgsNo:610542174127259688>')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        #User topic suggestions
        if payload.message_id in self.suggestion_msg_ids and payload.user_id != 639508517534957599:
            if payload.emoji.id == 580164400691019826:
                message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                await message.edit(content = 'Topic added', delete_after=6)
                #DOESNT ACTUALLY ADD THE TOPIC
            elif payload.emoji.id == 610542174127259688:
                message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                await message.edit(content = 'Topic removed', delete_after=6)

    @mod_and_above()
    @commands.command()
    @commands.cooldown(1, 5)
    async def remove_topic(self, ctx, index: int):
        """
            Delete topic by index.
            Usage: remove_topic index
        """
        if index < 1 or index > len(self.topics):
            await ctx.send(f'Invalid index. Min value: 0, Max value: {len(self.topics)}', delete_after=6)
            return await ctx.message.delete(delay=4)

        index = index - 1
        del self.topics[index]

        topic_file = open('topics.json', 'w')
        topic_file.write(json.dumps({"topics": self.topics}, indent=4))
        topic_file.close()
        await ctx.send('Topic removed.', delete_after=6)
        await ctx.message.delete(delay=4)

    @commands.command()
    async def find_topic(self, ctx, find: str):
        """
            Find a topic with fuzzy.
            Usage: find_topic the_topic
        """
        search_result = process.extractOne(find, self.topics)[0]

        embed = discord.Embed(title='Do you want to delete this topic?', description=search_result)
        message = await ctx.send(embed=embed)
        await message.add_reaction('<:kgsYes:580164400691019826>')
        await message.add_reaction('<:kgsNo:610542174127259688>')

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ('<:kgsYes:580164400691019826>','<:kgsNo:610542174127259688>')

        try:
            reaction, user = await self.bot.wait_for('reaction_add',timeout=20.0,check=check)  
        except asyncio.TimeoutError:
            await message.delete()
            return
        if str(reaction.emoji) == '<:kgsYes:580164400691019826>':
            await ctx.send("Will delete this topic")
        elif str(reaction.emoji) == '<:kgsNo:610542174127259688>':
            await message.delete()

def setup(bot):
    bot.add_cog(Fun(bot))
