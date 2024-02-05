import discord
import requests
from discord.ext import commands
from requests.models import PreparedRequest

from app.birdbot import BirdBot
from app.utils.config import Reference
from app.utils.helper import is_internal_command


class MessageEvents(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Mainbot only, Kgs server only
        # TextChannel and Thread only
        if not self.bot.ismainbot() or message.guild != self.bot.get_mainguild():
            return
        if not isinstance(message.channel, discord.TextChannel | discord.Thread):
            return
        await self.translate_bannsystem(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        # Mainbot only, Kgs server only, ignore bot edits
        # TextChannel and Thread only
        # Ignore moderation and log channels
        if not self.bot.ismainbot() or before.guild != self.bot.get_mainguild() or before.author.bot:
            return
        if not isinstance(before.channel, discord.TextChannel | discord.Thread):
            return
        if before.channel.category and before.channel.category.id == (
            Reference.Categories.moderation or Reference.Categories.server_logs
        ):
            return

        await self.log_message_edit(before, after)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        # Mainbot only, Kgs server only, ignore bot edits
        # TextChannel and Thread only
        # Ignore moderation and log channels
        if not self.bot.ismainbot() or message.guild != self.bot.get_mainguild() or message.author.bot:
            return
        if not isinstance(message.channel, discord.TextChannel | discord.Thread):
            return
        if message.channel.category and message.channel.category.id == (
            Reference.Categories.moderation or Reference.Categories.server_logs
        ):
            return

        if is_internal_command(self.bot, message):
            return

        await self.log_message_delete(message)

    async def log_message_delete(self, message: discord.Message):
        """
        Logs deleted message in the logging channel.
        """
        assert isinstance(message.channel, discord.TextChannel | discord.Thread)
        assert message.guild

        embed = discord.Embed(
            title="Message Deleted",
            description=f"Message deleted in {message.channel.mention}",
            color=0xC9322C,
            timestamp=discord.utils.utcnow(),
        )
        assert embed.description
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.add_field(name="Content", value=message.content)
        search_terms = f"```Deleted in {message.channel.id}"

        latest_logged_delete = [
            log async for log in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete)
        ][0]

        assert latest_logged_delete.user
        self_deleted = False
        if message.author == latest_logged_delete.target:
            embed.description += f"\nDeleted by {latest_logged_delete.user.mention} {latest_logged_delete.user.name}"
            search_terms += f"\nDeleted by {latest_logged_delete.user.id}"
        else:
            self_deleted = True
            search_terms += f"\nDeleted by {message.author.id}"
            embed.description += f"\nDeleted by {message.author.mention} {message.author.name}"

        search_terms += f"\nSent by {message.author.id}"
        search_terms += f"\nMessage from {message.author.id} deleted by {message.author.id if self_deleted else latest_logged_delete.user.id} in {message.channel.id}```"

        embed.add_field(name="Search terms", value=search_terms, inline=False)
        embed.set_footer(text="Input the search terms in your discord search bar to easily sort through specific logs")

        message_logging_channel = self.bot._get_channel(Reference.Channels.Logging.message_actions)
        await message_logging_channel.send(embed=embed)

    async def log_message_edit(self, before: discord.Message, after: discord.Message):
        """
        Logs message edits outside of the moderator category.
        """
        assert isinstance(before.channel, discord.TextChannel | discord.Thread)

        if before.content == after.content:
            return

        embed = discord.Embed(
            title="Message Edited",
            description=f"Message edited in {before.channel.mention}",
            color=0xEE7600,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=before.author.display_name, icon_url=before.author.display_avatar.url)
        embed.add_field(name="Before", value=before.content, inline=False)
        embed.add_field(name="After", value=after.content, inline=False)
        search_terms = f"""
                        ```Edited in {before.channel.id}\nEdited by {before.author.id}\nMessage edited in {before.channel.id} by {before.author.id}```
                        """

        embed.add_field(name="Search terms", value=search_terms, inline=False)
        embed.set_footer(text="Input the search terms in your discord search bar to easily sort through specific logs")

        message_logging_channel = self.bot._get_channel(Reference.Channels.Logging.message_actions)
        await message_logging_channel.send(embed=embed)

    async def translate_bannsystem(self, message: discord.Message):
        """
        Translate incoming bannsystem reports.
        """

        if not (
            message.channel.id == Reference.Channels.Logging.bannsystem and message.author.id == Reference.bannsystembot
        ):
            return

        embed = message.embeds[0].to_dict()
        assert "description" in embed and "fields" in embed
        to_translate = sum(
            [[embed["description"]], [field["value"] for field in embed["fields"]]], []
        )  # flatten without numpy

        embed["fields"][0]["name"] = "Reason"
        embed["fields"][1]["name"] = "Proof"

        url = "https://translate.birdbot.xyz/translate?"

        # TODO add keys in the future
        payload = {
            "q": " ### ".join(to_translate),
            "target": "en",
            "source": "de",
            "format": "text",
        }

        req = PreparedRequest()
        req.prepare_url(url, payload)
        assert req.url
        response = requests.request("POST", req.url, verify=False).json()

        replace_str = response["translatedText"].split(" ### ")
        embed["description"] = replace_str[0]
        embed["fields"][0]["value"] = replace_str[1]
        embed["fields"][1]["value"] = replace_str[2]
        to_send = discord.Embed.from_dict(embed)

        translated_msg = await message.channel.send(embed=to_send)

        await translated_msg.add_reaction(Reference.Emoji.PartialString.kgsYes)
        await translated_msg.add_reaction(Reference.Emoji.PartialString.kgsNo)
        await message.delete()


async def setup(bot: BirdBot):
    await bot.add_cog(MessageEvents(bot))
