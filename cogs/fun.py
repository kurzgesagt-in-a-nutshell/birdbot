import logging
import os
import json
import random
from re import search
import typing
from discord import colour
from fuzzywuzzy import process
import asyncio

import discord
from discord.ext import commands

from helper import mod_and_above
from database import topics_db


class Fun(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Fun')
        self.bot = bot

        self.topics = topics_db.find_one(
            {"name": "topics_list"})["topics"]  # Use this for DB interaction

        self.topics_list = self.topics  # Use this for user topics

        self.suggestion_msg_ids = []

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Fun')

    @commands.command()
    @commands.cooldown(1, 60)
    async def topic(self, ctx):
        """Get a topic to talk about."""
        if self.topics_list == []:
            self.topics_list = self.topics

        random_index = random.randint(0, len(self.topics_list)-1)
        await ctx.send(f'{self.topics_list.pop(random_index)}')

    @mod_and_above()
    @commands.command()
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
    async def add_topic(self, ctx, *, topic: str):
        """
            Add a topic to the list.
            Usage: add_topic topic_string
        """

        self.topics.append(topic)

        topics_db.update_one({"name": "topics_list"}, {
            "$set": {"topics": self.topics}})

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
        embed = discord.Embed(
            title=f'{ctx.author.name} suggested', description=topic, color=0xff0000)
        message = await automated_channel.send(embed=embed)
        self.suggestion_msg_ids.append(message.id)
        await message.add_reaction('<:kgsYes:580164400691019826>')
        await message.add_reaction('<:kgsNo:610542174127259688>')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # User topic suggestions
        if payload.message_id in self.suggestion_msg_ids and not payload.member.bot:
            if payload.emoji.id == 580164400691019826:
                message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                await message.edit(content='Topic added', delete_after=6)
                # DOESNT ACTUALLY ADD THE TOPIC
            elif payload.emoji.id == 610542174127259688:
                message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                await message.edit(content='Topic removed', delete_after=6)

    @mod_and_above()
    @commands.command()
    @commands.cooldown(1, 5)
    async def remove_topic(self, ctx, index: typing.Optional[int] = None, *, search_string: str = None):
        """
            Delete topic by index.
            Usage: remove_topic index
        """
        if index is not None:
            if index < 1 or index > len(self.topics):
                await ctx.send(f'Invalid index. Min value: 0, Max value: {len(self.topics)}', delete_after=6)
                return await ctx.message.delete(delay=4)

            index = index - 1
            topic = self.topics[index]
            del self.topics[index]

            topics_db.update_one({"name": "topics_list"}, {
                "$set": {"topics": self.topics}})

            emb = discord.Embed(
                title="Success", description=f'**{topic}** removed.', colour=discord.Colour.green())
            await ctx.send(embed=emb)

        else:
            if search_string is None:
                await ctx.send('Invalid arguments. Please specify either index or search string.', delete_after=6)
                return await ctx.message.delete(delay=4)

            search_result = process.extractBests(
                search_string, self.topics, limit=9)

            t = [topic[0] for topic in search_result if topic[1] > 75]

            if t == []:
                return await ctx.send("No match found.")

            embed_desc = ''.join(
                f'{index + 1}. {tp}\n' for index, tp in enumerate(t))

            embed = discord.Embed(
                title='React on corresponding number to delete topic.', description=embed_desc)

            msg = await ctx.send(embed=embed)

            emote_list = ["\u0031\uFE0F\u20E3", "\u0032\uFE0F\u20E3", "\u0033\uFE0F\u20E3", "\u0034\uFE0F\u20E3",
                          "\u0035\uFE0F\u20E3", "\u0036\uFE0F\u20E3", "\u0037\uFE0F\u20E3", "\u0038\uFE0F\u20E3", "\u0039\uFE0F\u20E3"]

            for emote in emote_list[:len(t)]:
                await msg.add_reaction(emote)

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in emote_list

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                i = emote_list.index(str(reaction.emoji))

                emb = discord.Embed(
                    title="Success!", description=f'**{self.topics[self.topics_list.index(search_result[i][0])]}** removed', colour=discord.Colour.green())

                await msg.edit(embed=emb)

                del self.topics[self.topics_list.index(search_result[i][0])]

                topics_db.update_one({"name": "topics_list"}, {
                    "$set": {"topics": self.topics}})

            except asyncio.TimeoutError:
                # await msg.delete()
                return

        # await ctx.message.delete(delay=4)


def setup(bot):
    bot.add_cog(Fun(bot))
