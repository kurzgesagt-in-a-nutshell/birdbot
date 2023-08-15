import logging
import json
import random
import typing
from fuzzywuzzy import process
import asyncio
import copy

import discord
from discord.ext import commands
from discord import app_commands

from utils import app_checks
from utils.config import Reference


class Topic(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Fun")
        self.bot = bot

        self.topics_db = self.bot.db.Topics
        self.topics = self.topics_db.find_one({"name": "topics"})[
            "topics"
        ]  # Use this for DB interaction

        self.topics_list = copy.deepcopy(
            self.topics
        )  # This is used to stop topic repeats

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Topic")

    topics_command = app_commands.Group(
        name="topics",
        description="Topic commands",
        guild_ids=[Reference.guild],
        default_permissions=discord.permissions.Permissions(manage_messages=True),
    )

    @app_commands.command()
    @app_commands.default_permissions(send_messages=True)
    @app_commands.guilds(Reference.guild)
    @app_checks.general_only()
    @app_checks.topic_perm_check()
    @app_commands.checks.cooldown(1, 300, key=lambda i: (i.guild_id, i.user.id))
    async def topic(self, interaction: discord.Interaction):
        """Fetches a random topic"""
        random_index = random.randint(0, len(self.topics_list) - 1)
        await interaction.response.send_message(f"{self.topics_list.pop(random_index)}")

        if self.topics_list == []:
            self.topics_list = copy.deepcopy(self.topics)

    @topics_command.command()
    @app_checks.mod_and_above()
    async def search(self, interaction: discord.Interaction, text: str):
        """Search a topic

        Parameters
        ----------
        text: str
            Search string
        """

        await interaction.response.defer(ephemeral=True)

        search_result = process.extractBests(text, self.topics, limit=9)

        t = [topic[0] for topic in search_result if topic[1] > 75]

        if t == []:
            return await interaction.edit_original_response(content="No match found.")

        embed_desc = "".join(
            f"{self.topics.index(tp) + 1}. {tp}\n" for _, tp in enumerate(t)
        )

        embed = discord.Embed(
            title="Best matches for search: ",
            description=embed_desc,
        )

        await interaction.edit_original_response(embed=embed)

    @topics_command.command()
    @app_checks.mod_and_above()
    async def add(self, interaction: discord.Interaction, text: str):
        """Add a topic

        Parameters
        ----------
        text: str
            New topic
        """

        self.topics.append(text)

        self.topics_db.update_one({"name": "topics"}, {"$set": {"topics": self.topics}})

        await interaction.response.send_message(
            f"Topic added at index {len(self.topics)}"
        )

    @topics_command.command()
    @app_checks.mod_and_above()
    async def remove(
        self,
        interaction: discord.Interaction,
        index: typing.Optional[int] = None,
        search_text: typing.Optional[str] = None,
    ):
        """Removes a topic

        Parameters
        ----------
        index: int
            Index of topic
        search_text: str
            Search string
        """

        if index is None and search_text is None:
            return await interaction.response.send_message(
                "Please provide value for one of the arguments.", ephemeral=True
            )

        await interaction.response.defer()

        if index is not None:
            if index < 1 or index > len(self.topics):
                return await interaction.edit_original_response(
                    content=f"Invalid index. Min value: 1, Max value: {len(self.topics)}"
                )

            index = index - 1
            topic = self.topics[index]
            del self.topics[index]

            self.topics_db.update_one(
                {"name": "topics"}, {"$set": {"topics": self.topics}}
            )

            emb = discord.Embed(
                title="Success",
                description=f"**{topic}** removed.",
                colour=discord.Colour.green(),
            )
            await interaction.edit_original_response(embed=emb)

        else:
            if search_text is None:
                return await interaction.edit_original_response(
                    content="Invalid arguments. Please specify either index or search string."
                )

            search_result = process.extractBests(search_text, self.topics, limit=9)

            t = [topic[0] for topic in search_result if topic[1] > 75]

            if t == []:
                return await interaction.edit_original_response(
                    content="No match found."
                )

            embed_desc = "".join(f"{index + 1}. {tp}\n" for index, tp in enumerate(t))

            embed = discord.Embed(
                title="React on corresponding number to delete topic.",
                description=embed_desc,
            )

            msg = await interaction.edit_original_response(embed=embed)

            emote_list = [
                "\u0031\uFE0F\u20E3",
                "\u0032\uFE0F\u20E3",
                "\u0033\uFE0F\u20E3",
                "\u0034\uFE0F\u20E3",
                "\u0035\uFE0F\u20E3",
                "\u0036\uFE0F\u20E3",
                "\u0037\uFE0F\u20E3",
                "\u0038\uFE0F\u20E3",
                "\u0039\uFE0F\u20E3",
            ]

            for emote in emote_list[: len(t)]:
                await msg.add_reaction(emote)

            def check(reaction, user):
                return user == interaction.user and str(reaction.emoji) in emote_list

            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=30.0, check=check
                )

                i = emote_list.index(str(reaction.emoji))

                emb = discord.Embed(
                    title="Success!",
                    description=f"**{search_result[i][0]}**\nremoved",
                    colour=discord.Colour.green(),
                )

                self.topics.remove(search_result[i][0])

                self.topics_db.update_one(
                    {"name": "topics"}, {"$set": {"topics": self.topics}}
                )

                await msg.edit(embed=emb)
                await msg.clear_reactions()

            except asyncio.TimeoutError:
                await msg.delete()
                return

    @app_commands.command()
    @app_commands.default_permissions(send_messages=True)
    @app_commands.guilds(Reference.guild)
    @app_commands.checks.cooldown(1, 60, key=lambda i: (i.guild_id, i.user.id))
    async def topic_suggest(self, interaction: discord.Interaction, topic: str):
        """Suggest a topic

        Parameters
        ----------
        topic: str
            Topic to suggest
        """
        await interaction.response.defer(ephemeral=True)
        automated_channel = self.bot.get_channel(Reference.Channels.banners_and_topics)
        embed = discord.Embed(description=f"**{topic}**", color=0xC8A2C8)
        embed.set_author(
            name=interaction.user.name + "#" + interaction.user.discriminator,
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_footer(text="topic")
        message = await automated_channel.send(embed=embed)

        await message.add_reaction("<:kgsYes:955703069516128307>")
        await message.add_reaction("<:kgsNo:955703108565098496>")

        await interaction.edit_original_response(
            content="Topic suggested.",
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # User topic suggestions
        if payload.channel_id == Reference.Channels.banners_and_topics and not payload.member.bot:
            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            mod_role = guild.get_role(Reference.Roles.moderator)
            if payload.member.top_role >= mod_role:
                message = await self.bot.get_channel(payload.channel_id).fetch_message(
                    payload.message_id
                )
                if message.embeds and message.embeds[0].footer.text == "topic":
                    if payload.emoji.id == Reference.Emoji.kgsYes:
                        topic = message.embeds[0].description
                        author = message.embeds[0].author
                        self.topics.append(topic.strip("*"))
                        self.topics_db.update_one(
                            {"name": "topics"}, {"$set": {"topics": self.topics}}
                        )
                        embed = discord.Embed(
                            description=f"**{topic}**", colour=discord.Colour.green()
                        )
                        embed.set_author(name=author.name, icon_url=author.icon_url)
                        await message.edit(embed=embed, delete_after=6)

                        member = guild.get_member_named(author.name)
                        try:
                            await member.send(
                                f"Your topic suggestion was accepted: **{topic}**"
                            )
                        except discord.Forbidden:
                            pass

                    elif payload.emoji.id == Reference.Emoji.kgsNo:
                        message = await self.bot.get_channel(
                            payload.channel_id
                        ).fetch_message(payload.message_id)
                        embed = discord.Embed(title="Suggestion removed!")
                        await message.edit(embed=embed, delete_after=6)


async def setup(bot):
    await bot.add_cog(Topic(bot))
