import logging
import json
import random
import typing
from fuzzywuzzy import process
import asyncio

import discord
from discord.ext import commands

from utils.helper import mod_and_above


class Topic(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Fun')
        self.bot = bot

        self.topics_db = self.bot.db.Topics
        self.topics = self.topics_db.find_one(
            {"name": "topics_list"})["topics"]  # Use this for DB interaction

        self.topics_list = self.topics  # This is used to stop topic repeats

        config_file = open('config.json', 'r')
        config_json = json.loads(config_file.read())
        config_file.close()

        self.mod_role = config_json['roles']['mod_role']
        self.automated_channel = config_json['logging']['automated_channel']

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Topic')

    @commands.group(invoke_without_command=True)
    @commands.cooldown(1, 60)
    async def topic(self, ctx):
        """Get a topic to talk about."""
        if self.topics_list == []:
            self.topics_list = self.topics

        random_index = random.randint(0, len(self.topics_list)-1)
        await ctx.send(f'{self.topics_list.pop(random_index)}')

    @mod_and_above()
    @topic.command()
    async def get(self, ctx, index: int):
        """
            Get a topic by index.
            Usage: topic get index
        """
        if index < 1 or index > len(self.topics):
            raise commands.BadArgument(
                message=f'Invalid index. Min value: 0, Max value: {len(self.topics)}')

        await ctx.send(f'{index}. {self.topics[index - 1]}')

    @mod_and_above()
    @topic.command()
    @commands.cooldown(1, 5)
    async def add(self, ctx, *, topic: str):
        """
            Add a topic to the list.
            Usage: topic add topic_string
        """

        self.topics.append(topic)

        self.topics_db.update_one({"name": "topics_list"}, {
            "$set": {"topics": self.topics}})

        await ctx.send(f'Topic added at index {len(self.topics)}', delete_after=6)
        await ctx.message.delete(delay=4)

    @topic.command()
    @commands.cooldown(1, 5)
    async def suggest(self, ctx, *, topic: str):
        """
            Suggest a topic.
            Usage: topic suggest topic_string
        """

        automated_channel = self.bot.get_channel(self.automated_channel)
        embed = discord.Embed(
            title=f'{ctx.author.name} suggested', description=f'**{topic}**', color=0xff0000)
        embed.set_footer(text='topic')
        message = await automated_channel.send(embed=embed)

        await message.add_reaction('<:kgsYes:580164400691019826>')
        await message.add_reaction('<:kgsNo:610542174127259688>')

        await ctx.send("Topic suggested.", delete_after=6)
        await ctx.message.delete(delay=4)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # User topic suggestions
        if payload.channel_id == self.automated_channel and not payload.member.bot:
            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            mod_role = guild.get_role(self.mod_role)
            if payload.member.top_role >= mod_role:
                message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                if message.embeds and message.embeds[0].footer.text == 'topic':
                    if payload.emoji.id == 580164400691019826:
                        topic = message.embeds[0].description
                        self.topics.append(topic.strip("*"))
                        self.topics_db.update_one({"name": "topics_list"}, {
                            "$set": {"topics": self.topics}})
                        embed = discord.Embed(
                            title="Topic added!", description=f'**{topic}**', colour=discord.Colour.green())
                        await message.edit(embed=embed)
                    elif payload.emoji.id == 610542174127259688:
                        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                        embed = discord.Embed(
                            title="Suggestion removed!")
                        await message.edit(embed=embed, delete_after=6)

    @mod_and_above()
    @topic.command()
    @commands.cooldown(1, 5)
    async def remove(self, ctx, index: typing.Optional[int] = None, *, search_string: str = None):
        """
            Delete topic by index or search string.
            Usage: topic remove index
        """
        if index is not None:
            if index < 1 or index > len(self.topics):
                raise commands.BadArgument(
                    message=f'Invalid index. Min value: 0, Max value: {len(self.topics)}')

            index = index - 1
            topic = self.topics[index]
            del self.topics[index]

            self.topics_db.update_one({"name": "topics_list"}, {
                "$set": {"topics": self.topics}})

            emb = discord.Embed(
                title="Success", description=f'**{topic}** removed.', colour=discord.Colour.green())
            await ctx.send(embed=emb)

        else:
            if search_string is None:
                raise commands.BadArgument(
                    message='Invalid arguments. Please specify either index or search string.')

            await ctx.message.delete(delay=6)

            search_result = process.extractBests(
                search_string, self.topics, limit=9)

            t = [topic[0] for topic in search_result if topic[1] > 75]

            if t == []:
                return await ctx.send("No match found.", delete_after=6)

            embed_desc = ''.join(
                f'{index + 1}. {tp}\n' for index, tp in enumerate(t))

            embed = discord.Embed(
                title='React on corresponding number to delete topic.', description=embed_desc)

            msg = await ctx.send(embed=embed)

            emote_list = [
                "\u0031\uFE0F\u20E3", "\u0032\uFE0F\u20E3", "\u0033\uFE0F\u20E3",
                "\u0034\uFE0F\u20E3", "\u0035\uFE0F\u20E3", "\u0036\uFE0F\u20E3",
                "\u0037\uFE0F\u20E3", "\u0038\uFE0F\u20E3", "\u0039\uFE0F\u20E3"]

            for emote in emote_list[:len(t)]:
                await msg.add_reaction(emote)

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in emote_list

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                i = emote_list.index(str(reaction.emoji))

                emb = discord.Embed(
                    title="Success!", description=f'**{search_result[i][0]}**\nremoved', colour=discord.Colour.green())

                await msg.edit(embed=emb, delete_after=6)

                self.topics.remove(search_result[i][0])

                self.topics_db.update_one({"name": "topics_list"}, {
                    "$set": {"topics": self.topics}})

            except asyncio.TimeoutError:
                await msg.delete()
                return


def setup(bot):
    bot.add_cog(Topic(bot))
