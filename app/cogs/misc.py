import asyncio
import json
import logging
import re
import typing

import demoji
import discord
import pymongo
from discord import app_commands
from discord.ext import commands

from app.utils import checks
from app.utils.config import Reference

import birdbot


class Misc(commands.Cog):
    def __init__(self, bot: birdbot.BirdBot):
        self.logger = logging.getLogger("Misc")
        self.bot = bot
        self.intro_db = self.bot.db.StaffIntros
        self.kgs_guild: typing.Optional[discord.Guild] = None
        self.role_precendence = (
            915629257470906369,
            414029841101225985,
            414092550031278091,
            1058243220817063936,
            681812574026727471,
        )
        with open("config.json", "r") as f:
            self.config = json.load(f)

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Loaded Misc Cog")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick == after.nick:
            return

        self.kgs_guild: discord.Guild = self.bot.get_guild(Reference.guild)
        assert self.kgs_guild != None

        subreddit_role = discord.utils.get(
            self.kgs_guild.roles, id=Reference.Roles.subreddit_mod
        )
        if not after.top_role >= subreddit_role:
            return

        intro = self.intro_db.find_one({"_id": before.id})
        intro_channel = self.kgs_guild.get_channel(Reference.Channels.intro_channel)
        assert intro_channel != None

        msg = await intro_channel.fetch_message(intro["message_id"])
        embed = msg.embeds[0]
        embed.set_author(name=after.display_name, icon_url=after.avatar.url)
        await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):

        self.kgs_guild = self.bot.get_guild(Reference.guild)
        assert self.kgs_guild != None

        member = self.kgs_guild.get_member(before.id)
        if not member:
            return
        subreddit_role = discord.utils.get(
            self.kgs_guild.roles, id=Reference.Roles.subreddit_mod
        )
        if not member.top_role >= subreddit_role:
            return

        intro = self.intro_db.find_one({"_id": before.id})
        intro_channel = self.kgs_guild.get_channel(Reference.Channels.intro_channel)
        msg = await intro_channel.fetch_message(intro["message_id"])
        embed = msg.embeds[0]
        embed.set_author(name=member.display_name, icon_url=after.avatar.url)
        await msg.edit(embed=embed)

    @app_commands.command()
    @checks.devs_only()
    async def intro(self, interaction: discord.Interaction):
        """
        Staff intro command, create or edit an intro
        """
        oldIntro = self.intro_db.find_one({"_id": interaction.user.id})
        await interaction.response.send_modal(
            IntroModal(oldIntro=oldIntro, bot=self.bot)
        )

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.checks.cooldown(1, 10)
    @checks.bot_commands_only()
    async def big_emote(self, interaction: discord.Interaction, emoji: str):
        """Get image for server emote

        Parameters
        ----------
        emoji: str
            Discord Emoji (only use in #bot-commands)
        """
        """
        if len(args) > 1:
            ctx.send("Please only send one emoji at a time")
        """
        print(len(demoji.findall_list(emoji)))
        if len(demoji.findall_list(emoji)) == 1:
            code = (
                str(emoji.encode("unicode-escape"))
                .replace("U000", "-")
                .replace("\\", "")
                .replace("'", "")
                .replace("u", "-")[2:]
            )
            print(code)
            name = (
                demoji.replace_with_desc(emoji)
                .replace(" ", "-")
                .replace(":", "")
                .replace("_", "-")
            )
            await interaction.response.send_message(
                "https://em-content.zobj.net/thumbs/160/twitter/322/"
                + name
                + "_"
                + code
                + ".png"
            )
        elif len(demoji.findall_list(emoji)) > 1:
            await interaction.response.send_message("please only send one emoji")
        else:
            if re.match(r"<a:\w+:(\d{17,19})>", str(emoji)):
                emoji = str(re.findall(r"<a:\w+:(\d{17,19})>", str(emoji))[0]) + ".gif"
                await interaction.response.send_message(
                    "https://cdn.discordapp.com/emojis/" + str(emoji)
                )
            elif re.match(r"<:\w+:(\d{17,19})>", str(emoji)):
                print("png")
                emoji = str(re.findall(r"<:\w+:(\d{17,19})>", str(emoji))[0]) + ".png"
                await interaction.response.send_message(
                    "https://cdn.discordapp.com/emojis/" + str(emoji)
                )
            else:
                await interaction.response.send_message("Could not process this emoji")


async def setup(bot):
    await bot.add_cog(Misc(bot))


class IntroModal(discord.ui.Modal):
    """
    The modal UI for intro commands.
    """

    def __init__(self, oldIntro, bot: birdbot.BirdBot):
        super().__init__(title="Introduce yourself!")
        self.oldIntro = oldIntro
        self.intro_db = bot.db.StaffIntros

        assert self.kgs_guild != None
        self.kgs_guild = bot.get_guild(Reference.guild)

        timezone_ph = bio_ph = image_ph = None
        timezone_default = bio_default = image_default = None
        if oldIntro:
            timezone_default = oldIntro["tz_text"]
            bio_default = oldIntro["bio"]
            image_default = oldIntro["image"]
        else:
            timezone_ph = "The internet - UTC | GMT+0:00"
            bio_ph = "Hello! I'm Birdbot and I help run this server."
            image_ph = "https://cdn.discordapp.com/avatars/471705718957801483/cfcf7fbcdc9579d7f0606b014aa1ede8.png"

        self.timezone = discord.ui.TextInput(
            label="Enter your timezone.",
            style=discord.TextStyle.short,
            required=True,
            placeholder=timezone_ph,
            default=timezone_default,
            max_length=90,
        )

        self.bio = discord.ui.TextInput(
            label="Enter your bio.",
            style=discord.TextStyle.paragraph,
            required=True,
            placeholder=bio_ph,
            default=bio_default,
        )

        self.image = discord.ui.TextInput(
            label="Enter the image link for your personal bird.",
            style=discord.TextStyle.short,
            required=True,
            placeholder=image_ph,
            default=image_default,
        )

        self.add_item(self.timezone)
        self.add_item(self.bio)
        self.add_item(self.image)

    def get_footer(self, role: discord.Role) -> typing.Tuple[str, str | None]:
        """Make the footer with role name and icon"""
        footer_name = (
            "Kurzgesagt Official"
            if role.id == Reference.Roles.kgsofficial
            else role.name
        )
        if role.icon:
            footer_icon = role.icon.url
        else:
            footer_icon = None
        return footer_name, footer_icon

    def edit_embed(
        self, oldIntroMessage: discord.Message
    ) -> typing.Tuple[discord.Embed, bool]:
        """Edit and return the intro embed"""
        embed = oldIntroMessage.embeds[0]

        embed.description = f"**{self.timezone_txt}**\n\n" + self.bio_txt
        embed.set_thumbnail(url=self.image.value)
        embed.set_author(
            name=self.user.display_name,
            icon_url=self.user.avatar.url
            if self.user.avatar
            else self.user.display_avatar.url,
        )

        # check if the user's top role has changed (promotion/demotion)
        if (embed.footer.text == self.role.name) or (
            embed.footer.text == "Kurzgesagt Official"
            and self.role.id == Reference.Roles.kgsofficial
        ):
            reorder = False
        else:
            footer_name, footer_icon = self.get_footer(self.role)

            embed.set_footer(text=footer_name, icon_url=footer_icon)
            embed.color = self.role.color

            reorder = True

        return embed, reorder

    def create_embed(self) -> discord.Embed:
        """Make and return a new intro embed"""
        description = f"**{self.timezone_txt}**\n\n" + self.bio_txt

        footer_name, footer_icon = self.get_footer(self.role)

        embed = discord.Embed(description=description, color=self.role.color)
        embed.set_author(
            name=self.user.display_name,
            icon_url=self.user.avatar.url
            if self.user.avatar
            else self.user.display_avatar.url,
        )
        embed.set_footer(text=footer_name, icon_url=footer_icon)
        embed.set_thumbnail(url=self.image.value)

        return embed

    async def reorder(
        self,
        embed: discord.Embed,
    ):
        """Deletes intros that are before role_id, sends the edited/new intro, then adds the deleted intros back"""

        # make a list of embeds that have to be deleted (doc, embed)
        embeds = []
        async for message in self.intro_channel.history():
            if not message.embeds:
                break

            if message.embeds[0].footer.text == self.role.name:
                break

            doc = self.intro_db.find_one({"message_id": message.id})
            if doc:
                embeds.append((doc, message.embeds[0]))
                await message.delete()

        # now we can send the new intro message
        msg = await self.intro_channel.send(embed=embed)
        self.intro_db.update_one(
            {"_id": self.user.id}, {"$set": {"message_id": msg.id}}
        )

        # add the deleted embeds back
        if embeds:
            for doc, embed in embeds:
                msg = await self.intro_channel.send(embed=embed)
                self.intro_db.update_one(
                    {"_id": doc["_id"]}, {"$set": {"message_id": msg.id}}
                )

    def add_emojis(self, text: str) -> str:
        """Add server emojis, because modals don't support them"""
        # make a simplified version of emojis
        serverEmojis: dict = {}
        for emoji in self.kgs_guild.emojis:
            serverEmojis = {f":{emoji.name}:": emoji.id}

        return re.sub(
            r"(?<!<):[A-Za-z0-9_.]+:(?![0-9]+>)",
            lambda emoji: f"<{emoji.group()}{serverEmojis[emoji.group()]}>"
            if emoji.group() in serverEmojis
            else emoji.group(),
            text,
        )

    async def on_submit(self, interaction: discord.Interaction):
        """Most of the intro command logic is here"""
        oldIntroMessage = None  # if we're adding a new intro this will remain None

        self.user = self.kgs_guild.get_member(interaction.user.id)
        self.role = self.user.top_role
        self.intro_channel = self.kgs_guild.get_channel(
            Reference.Channels.intro_channel
        )

        self.timezone_txt = self.add_emojis(self.timezone.value)
        self.bio_txt = self.add_emojis(self.bio.value)
        self.image_txt = self.image.value

        # update mongo
        if self.oldIntro:
            self.intro_db.update_one(
                {"_id": self.user.id},
                {
                    "$set": {
                        "tz_text": self.timezone_txt,
                        "bio": self.bio_txt,
                        "image": self.image.value,
                    }
                },
            )
        else:
            self.intro_db.insert_one(
                {
                    "_id": self.user.id,
                    "tz_text": self.timezone_txt,
                    "bio": self.bio_txt,
                    "message_id": None,  # we will edit it with message id after reordering
                    "image": self.image.value,
                }
            )

        # check the validity of the image link, write a better regex?
        if not re.match(r"^https*://.*\..*", self.image.value):
            await interaction.response.send_message(
                "Incorrect image link, please try again", ephemeral=True
            )
            return

        # check if the message was deleted for some reason
        if self.oldIntro:
            if self.oldIntro["message_id"]:
                try:
                    oldIntroMessage = await self.intro_channel.fetch_message(
                        self.oldIntro["message_id"]
                    )
                except discord.NotFound:
                    # the message was deleted, but not to worry we will just create a new one
                    pass

        if oldIntroMessage:
            embed, reorder = self.edit_embed(oldIntroMessage)
            await interaction.response.send_message(
                "Your intro will be edited!", ephemeral=True
            )
            if not reorder:
                await oldIntroMessage.edit(embed=embed)
            else:
                await self.reorder(embed)

        else:
            embed = self.create_embed()

            await interaction.response.send_message(
                "Your intro will be added!", ephemeral=True
            )

            await self.reorder(embed)
