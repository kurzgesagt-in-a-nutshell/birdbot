import asyncio
import logging
import re
import typing
from typing import TYPE_CHECKING

import discord
from discord import Interaction, app_commands
from discord import ui as dui
from discord.ext import commands
from fuzzywuzzy import process
from pymongo.errors import CollectionInvalid

from app.birdbot import BirdBot
from app.utils import checks, errors
from app.utils.config import Reference
from app.utils.helper import TopicCycle

if TYPE_CHECKING:
    from pymongo.collection import Collection


class TopicEditorModal(dui.Modal):
    """
    A modal sent to the user attempting to change the topic
    """

    topic = dui.TextInput(
        label="Topic", placeholder="Edited topic goes here", style=discord.TextStyle.long, max_length=2000
    )

    def __init__(self, topic: str):
        super().__init__(title="Topic Editor", timeout=60 * 2)
        self.topic.default = topic

    async def on_submit(self, interaction: Interaction) -> None:
        """
        Edits the message if the input value is different than the default
        """
        if self.topic.value == self.topic.default:
            await interaction.response.defer(thinking=False)
            return

        message = interaction.message
        assert message
        embed = message.embeds[0]

        embed.description = self.topic.value

        embed.add_field(name="Initial Submission", value=self.topic.default)

        await interaction.response.edit_message(embed=embed)


class TopicAcceptorView(dui.View):
    """
    A class that is meant to be instantiated once and used on all topic
    suggestions
    """

    def __init__(self, accept_id: str, deny_id: str, edit_id: str, topics: list, topic_db):
        super().__init__(timeout=None)

        self._accept.custom_id = accept_id
        self._deny.custom_id = deny_id
        self._edit.custom_id = edit_id

        self.topics = topics
        self.topics_db: Collection = topic_db
        self.editing = {}

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Checks if another user is currently editing this topic.
        """
        assert interaction.message
        editing = self.editing.get(interaction.message.id, 0)
        if editing != 0:
            who = f"<@{editing}> is currently editing this topic"
            avoid = (
                ""
                if editing != interaction.user.id
                else "\nThis interaction will clear out in at least two minutes."
                + " To avoid this issue, do not cancel out of the popup"
            )

            raise errors.InvalidAuthorizationError(content=f"{who}{avoid}")
        return True

    async def on_error(self, interaction: Interaction, error: Exception, item: dui.Item):
        """Raises the error to the command tree"""
        await interaction.client.tree.on_error(interaction, error)  # type: ignore

    @dui.button(
        label="Accept",
        style=discord.ButtonStyle.green,
        emoji=discord.PartialEmoji.from_str(Reference.Emoji.PartialString.kgsYes),
    )
    async def _accept(self, interaction: Interaction, button: dui.Button):
        """
        Accepts the topic and removes the view from the message
        Changes the embed to indicate it was accepted and by who
        """
        message = interaction.message
        assert message
        embed = message.embeds[0]

        topic = embed.description
        self.topics.append(topic)
        self.topic_db.update_one({"name": "topics"}, {"$set": {"topics": self.topics}})  # type: ignore

        TopicCycle().queue_last(topic)

        embed.color = discord.Color.green()
        embed.title = f"Accepted by {interaction.user.name}"

        await interaction.response.edit_message(embed=embed, view=None)

        try:
            assert embed.author.name
            match = re.match(r".*\(([0-9]+)\)$", embed.author.name)
            if match:
                userid = match.group(1)
                suggester = await interaction.client.fetch_user(int(userid))
                await suggester.send(f"Your topic suggestion was accepted: **{topic}**")

        except discord.Forbidden:
            pass

    @dui.button(
        label="Deny",
        style=discord.ButtonStyle.danger,
        emoji=discord.PartialEmoji.from_str(Reference.Emoji.PartialString.kgsNo),
    )
    async def _deny(self, interaction: Interaction, button: dui.Button):
        """
        Denys the topic and removes the view from the message
        Changes the embed to indicate it was denied and by who
        """
        message = interaction.message
        assert message
        embed = message.embeds[0]

        embed.color = discord.Color.red()
        embed.title = f"Denied by {interaction.user.name}"

        await interaction.response.edit_message(embed=embed, view=None)

    @dui.button(
        label="Edit",
        style=discord.ButtonStyle.blurple,
        emoji=discord.PartialEmoji.from_str(Reference.Emoji.PartialString.kgsWhoAsked),
    )
    async def _edit(self, interaction: Interaction, button: dui.Button):
        """
        Sends a modal to interact with the provided topic text
        """
        assert interaction.message
        self.editing[interaction.message.id] = interaction.user.id

        embed = interaction.message.embeds[0]
        assert embed.description

        topic_modal = TopicEditorModal(embed.description)
        await interaction.response.send_modal(topic_modal)

        await topic_modal.wait()
        self.editing.pop(interaction.message.id)


class Topic(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.logger = logging.getLogger("Fun")
        self.bot = bot

        self.topics_db: Collection = self.bot.db.Topics
        topics_find = self.topics_db.find_one({"name": "topics"})
        if topics_find == None:
            raise CollectionInvalid
        self.topics: typing.List = topics_find["topics"]  # Use this for DB interaction

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Topic")

    async def cog_load(self):
        self.TOPIC_ACCEPT = f"TOPIC-ACCEPT-{self.bot._user().id}"
        self.TOPIC_DENY = f"TOPIC-DENY-{self.bot._user().id}"
        self.TOPIC_EDIT = f"TOPIC-EDIT-{self.bot._user().id}"

        self.TOPIC_VIEW = TopicAcceptorView(
            accept_id=self.TOPIC_ACCEPT,
            deny_id=self.TOPIC_DENY,
            edit_id=self.TOPIC_EDIT,
            topics=self.topics,
            topic_db=self.topics_db,
        )

        self.bot.add_view(self.TOPIC_VIEW)

        self.topics_cycle = TopicCycle(self.topics)

    async def cog_unload(self) -> None:
        self.TOPIC_VIEW.stop()

    topics_command = app_commands.Group(
        name="topics",
        description="Topic commands",
        guild_ids=[Reference.guild],
        default_permissions=discord.permissions.Permissions(manage_messages=True),
    )

    @app_commands.command()
    @app_commands.default_permissions(send_messages=True)
    @app_commands.guilds(Reference.guild)
    @checks.general_only()
    @checks.topic_perm_check()
    @app_commands.checks.cooldown(1, 300, key=lambda i: (i.guild_id, i.user.id))
    async def topic(self, interaction: discord.Interaction):
        """Fetches a random topic"""
        topic = next(self.topics_cycle)
        await interaction.response.send_message(f"{topic}")

    @topics_command.command()
    @checks.mod_and_above()
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

        embed_desc = "".join(f"{self.topics.index(tp) + 1}. {tp}\n" for _, tp in enumerate(t))

        embed = discord.Embed(
            title="Best matches for search: ",
            description=embed_desc,
        )

        await interaction.edit_original_response(embed=embed)

    @topics_command.command()
    @checks.mod_and_above()
    async def add(self, interaction: discord.Interaction, text: str):
        """Add a topic

        Parameters
        ----------
        text: str
            New topic
        """

        self.topics.append(text)

        self.topics_db.update_one({"name": "topics"}, {"$set": {"topics": self.topics}})

        TopicCycle().queue_last(text)

        await interaction.response.send_message(f"Topic added.")

    @topics_command.command()
    @checks.mod_and_above()
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
        topics_find = self.topics_db.find_one({"name": "topics"})
        if topics_find == None:
            raise CollectionInvalid
        self.topics = topics_find["topics"]

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

            self.topics_db.update_one({"name": "topics"}, {"$set": {"topics": self.topics}})

            TopicCycle().queue_remove(topic)

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
                return await interaction.edit_original_response(content="No match found.")

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
                reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)

                i = emote_list.index(str(reaction.emoji))

                emb = discord.Embed(
                    title="Success!",
                    description=f"**{search_result[i][0]}**\nremoved",
                    colour=discord.Colour.green(),
                )

                self.topics.remove(search_result[i][0])

                self.topics_db.update_one({"name": "topics"}, {"$set": {"topics": self.topics}})

                TopicCycle().queue_remove(search_result[i][0])

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
        automated_channel = self.bot._get_channel(Reference.Channels.banners_and_topics)
        embed = discord.Embed(description=topic, color=0xC8A2C8)
        embed.set_author(
            name=f"{interaction.user.name} ({interaction.user.id})",
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_footer(text="topic")
        await automated_channel.send(embed=embed, view=self.TOPIC_VIEW)

        await interaction.edit_original_response(
            content="Topic suggested.",
        )


async def setup(bot: BirdBot):
    await bot.add_cog(Topic(bot))
