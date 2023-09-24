import asyncio
import json
import logging
import re
import typing

import birdbot
import demoji
import discord
import pymongo
from discord import app_commands
from discord.ext import commands

from app.birdbot import BirdBot
from app.utils import checks
from app.utils.config import Reference


class Misc(commands.Cog):
    def __init__(self, bot: BirdBot):
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

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("Loaded Misc Cog")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick == after.nick:
            return

        self.kgs_guild: discord.Guild = self.bot.get_guild(Reference.guild)
        assert self.kgs_guild != None

        subreddit_role = discord.utils.get(self.kgs_guild.roles, id=Reference.Roles.subreddit_mod)
        if not after.top_role >= subreddit_role:
            return

        async with IntroLock.reorder_lock:
            await self.edit_intro(after)

    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        self.kgs_guild = self.bot.get_guild(Reference.guild)
        assert self.kgs_guild != None

        member = self.kgs_guild.get_member(before.id)
        if not member:
            return
        subreddit_role = discord.utils.get(self.kgs_guild.roles, id=Reference.Roles.subreddit_mod)
        if not member.top_role >= subreddit_role:
            return

        async with IntroLock.reorder_lock:
            await self.edit_intro(after)

    async def edit_intro(self, member):
        intro = self.intro_db.find_one({"_id": member.id})
        if not intro:
            return
        intro_channel = self.kgs_guild.get_channel(Reference.Channels.intro_channel)
        msg = await intro_channel.fetch_message(intro["message_id"])
        embed = msg.embeds[0]
        if embed.author.name != member.display_name or embed.author.icon_url != member.avatar.url:
            embed.set_author(name=member.display_name, icon_url=member.avatar.url)
            await msg.edit(embed=embed)

    @app_commands.command()
    @checks.role_and_above(Reference.Roles.subreddit_mod)
    async def intro(self, interaction: discord.Interaction):
        """
        Staff intro command, create or edit an intro
        """
        oldIntro: dict = self.intro_db.find_one({"_id": interaction.user.id})
        await interaction.response.send_modal(IntroModal(oldIntro=oldIntro, bot=self.bot))

    @app_commands.command()
    @checks.admin_and_above()
    async def intro_reorg(self, interaction: discord.Interaction):
        """
        Admin intro command, reorganize all intros
        """
        """Delete demoted entries in mongo, purge the channel and send all up to date intro embeds"""

        await interaction.response.send_message("Will be done!", ephemeral=True)

        def make_intro_embed(member: discord.Member, introDoc) -> discord.Embed:
            description = f'**{introDoc["tz_text"]}**\n\n' + introDoc["bio"]
            role = member.top_role
            footer_name = "Kurzgesagt Official" if role.id == Reference.Roles.kgsmaintenance else role.name
            if role.icon:
                footer_icon = role.icon.url
            else:
                footer_icon = None

            embed = discord.Embed(description=description, color=member.color)
            embed.set_author(
                name=member.display_name,
                icon_url=member.avatar.url if member.avatar else member.display_avatar.url,
            )
            embed.set_footer(text=footer_name, icon_url=footer_icon)
            embed.set_thumbnail(url=introDoc["image"])

            return embed

        kgs_guild: discord.Guild = self.bot.get_guild(Reference.guild)

        lowest_role = kgs_guild.get_role(Reference.Roles.subreddit_mod)

        embedList: typing.List[typing.Tuple[discord.Embed, discord.Member]] = []
        for introDoc in self.intro_db.find():
            member = kgs_guild.get_member(introDoc["_id"])

            if not member or member.top_role < lowest_role:
                self.intro_db.delete_one(introDoc)
                continue

            embed = make_intro_embed(member, introDoc)

            embedList.append((embed, member))

        def embed_sort(e: typing.Tuple[discord.Embed, discord.Member]) -> int:
            return e[1].top_role.position

        embedList.sort(key=embed_sort, reverse=True)

        intro_channel: discord.TextChannel = kgs_guild.get_channel(Reference.Channels.intro_channel)

        def purge_check(msg: discord.Message) -> bool:
            return bool(msg.author == self.bot.user and msg.embeds and msg.embeds[0].type == "rich")

        # limit is currently 100 because getting the length of the collection is annoying
        await intro_channel.purge(check=purge_check, limit=100)

        for embed, member in embedList:
            msg = await intro_channel.send(embed=embed)
            self.intro_db.update_one({"_id": member.id}, {"$set": {"message_id": msg.id}})

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
            name = demoji.replace_with_desc(emoji).replace(" ", "-").replace(":", "").replace("_", "-")
            await interaction.response.send_message(
                "https://em-content.zobj.net/thumbs/160/twitter/322/" + name + "_" + code + ".png"
            )
        elif len(demoji.findall_list(emoji)) > 1:
            await interaction.response.send_message("please only send one emoji")
        else:
            if re.match(r"<a:\w+:(\d{17,19})>", str(emoji)):
                emoji = str(re.findall(r"<a:\w+:(\d{17,19})>", str(emoji))[0]) + ".gif"
                await interaction.response.send_message("https://cdn.discordapp.com/emojis/" + str(emoji))
            elif re.match(r"<:\w+:(\d{17,19})>", str(emoji)):
                print("png")
                emoji = str(re.findall(r"<:\w+:(\d{17,19})>", str(emoji))[0]) + ".png"
                await interaction.response.send_message("https://cdn.discordapp.com/emojis/" + str(emoji))
            else:
                await interaction.response.send_message("Could not process this emoji")


async def setup(bot):
    await bot.add_cog(Misc(bot))


class IntroModal(discord.ui.Modal):
    """
    The modal UI for intro commands.
    """

    def __init__(self, oldIntro: dict, bot: BirdBot):
        super().__init__(title="Introduce yourself!")

        self.logger = logging.getLogger("Misc")

        self.oldIntro = oldIntro
        self.intro_db = bot.db.StaffIntros

        self.kgs_guild: discord.Guild = bot.get_guild(Reference.guild)

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
        footer_name = "Kurzgesagt Official" if role.id == Reference.Roles.kgsmaintenance else role.name
        if role.icon:
            footer_icon = role.icon.url
        else:
            footer_icon = None
        return footer_name, footer_icon

    def create_embed(self) -> discord.Embed:
        """Make and return a new intro embed"""
        description = f"**{self.timezone_txt}**\n\n" + self.bio_txt

        footer_name, footer_icon = self.get_footer(self.role)

        embed = discord.Embed(description=description, color=self.user.color)
        embed.set_author(
            name=self.user.display_name,
            icon_url=self.user.avatar.url if self.user.avatar else self.user.display_avatar.url,
        )
        embed.set_footer(text=footer_name, icon_url=footer_icon)
        embed.set_thumbnail(url=self.image.value)

        return embed

    def add_emojis(self, text: str) -> str:
        """Add server emojis, because modals don't support them"""
        # make a simplified version of emojis
        serverEmojis: dict = {}
        for emoji in self.kgs_guild.emojis:
            serverEmojis = {f":{emoji.name}:": emoji.id}

        return re.sub(
            r"(?<!<):[A-Za-z0-9_]+:(?![0-9]+>)",
            lambda emoji: f"<{emoji.group()}{serverEmojis[emoji.group()]}>"
            if emoji.group() in serverEmojis
            else emoji.group(),
            text,
        )

    async def reorder_demotion(self, oldmessage: discord.Message):
        # make a list of messages that have to be edited (doc, msg)
        # limit = self.intro_db.count_documents({})
        limit = 100
        embeds: typing.List[typing.Tuple[dict, discord.Message]] = []
        newPos = 0
        embeds.append((self.oldIntro, oldmessage))
        snowflake = discord.Object(self.oldIntro["message_id"])
        async for message in self.intro_channel.history(limit=limit, after=snowflake, oldest_first=True):
            if not message.embeds:
                continue
            if not message.embeds[0].footer:
                continue

            doc = self.intro_db.find_one({"message_id": message.id})
            if not doc:
                continue

            embeds.append((doc, message))

            rolename = (
                message.embeds[0].footer.text
                if message.embeds[0].footer.text != "Kurzgesagt Official"
                else "Kurzgesagt Maintenance"
            )
            msgrole = discord.utils.find(lambda role: role.name == rolename, self.kgs_guild.roles)

            if self.role >= msgrole:
                break

            newPos += 1

        self.logger.info(f"the new pos {newPos}")

        for i in range(1, newPos + 1):
            msg = embeds[i - 1][1]
            await msg.edit(embed=embeds[i][1].embeds[0])

            self.intro_db.update_one({"_id": embeds[i][0]["_id"]}, {"$set": {"message_id": msg.id}})

        doc, msg = embeds[newPos]

        embed = self.create_embed()
        await msg.edit(embed=embed)
        self.intro_db.update_one({"_id": self.user.id}, {"$set": {"message_id": msg.id}})

    async def reorder_promotion(self, oldmessage: discord.Message):
        # make a list of messages that have to be edited (doc, msg)
        # limit = self.intro_db.count_documents({})
        limit = 100
        embeds: typing.List[typing.Tuple[dict, discord.Message]] = []
        newPos = 0
        embeds.append((self.oldIntro, oldmessage))
        self.logger.info(f"Old message: {self.oldIntro['message_id']}")
        snowflake = discord.Object(self.oldIntro["message_id"])
        async for message in self.intro_channel.history(limit=limit, before=snowflake, oldest_first=False):
            if not message.embeds:
                continue
            if not message.embeds[0].footer:
                continue

            doc = self.intro_db.find_one({"message_id": message.id})
            if not doc:
                continue

            embeds.append((doc, message))

            rolename = (
                message.embeds[0].footer.text
                if message.embeds[0].footer.text != "Kurzgesagt Official"
                else "Kurzgesagt Maintenance"
            )
            msgrole = discord.utils.find(lambda role: role.name == rolename, self.kgs_guild.roles)

            if self.role <= msgrole:
                break

            newPos += 1

        for i in range(1, newPos + 1):
            msg = embeds[i - 1][1]
            await msg.edit(embed=embeds[i][1].embeds[0])

            self.intro_db.update_one({"_id": embeds[i][0]["_id"]}, {"$set": {"message_id": msg.id}})

        doc, msg = embeds[newPos]

        embed = self.create_embed()
        await msg.edit(embed=embed)
        self.intro_db.update_one({"_id": self.user.id}, {"$set": {"message_id": msg.id}})

    async def reorder_add(self):
        # make a list of messages that have to be edited (doc, msg)
        # limit = self.intro_db.count_documents({})
        limit = 100
        embeds: typing.List[typing.Tuple[dict, discord.Message]] = []
        newPos = 0
        async for message in self.intro_channel.history(limit=limit, oldest_first=False):
            if not message.embeds:
                continue
            if not message.embeds[0].footer:
                continue

            doc = self.intro_db.find_one({"message_id": message.id})
            if not doc:
                continue

            rolename = (
                message.embeds[0].footer.text
                if message.embeds[0].footer.text != "Kurzgesagt Official"
                else "Kurzgesagt Maintenance"
            )
            msgrole = discord.utils.find(lambda role: role.name == rolename, self.kgs_guild.roles)

            embeds.append((doc, message))

            if msgrole >= self.role:
                break

            newPos += 1

        newembed = self.create_embed()

        if newPos == 0:
            msg = await self.intro_channel.send(embed=newembed)
            self.intro_db.update_one({"_id": self.user.id}, {"$set": {"message_id": msg.id}})
            return

        for i in range(1, newPos):
            msg = embeds[i - 1][1]
            await msg.edit(embed=embeds[i][1].embeds[0])

            self.intro_db.update_one({"_id": embeds[i][0]["_id"]}, {"$set": {"message_id": msg.id}})

        doc, message = embeds[0]
        msg = await self.intro_channel.send(embed=message.embeds[0])
        self.intro_db.update_one({"_id": doc["_id"]}, {"$set": {"message_id": msg.id}})
        doc, message = embeds[newPos - 1]
        self.intro_db.update_one({"_id": self.user.id}, {"$set": {"message_id": message.id}})
        await message.edit(embed=newembed)

    async def on_submit(self, interaction: discord.Interaction):
        """Most of the intro command logic is here"""
        oldIntroMessage = None  # if we're adding a new intro this will remain None

        self.user: discord.Member = self.kgs_guild.get_member(interaction.user.id)
        assert self.user
        self.role = self.user.top_role
        self.intro_channel: discord.TextChannel = self.kgs_guild.get_channel(Reference.Channels.intro_channel)

        self.timezone_txt = self.add_emojis(self.timezone.value)
        self.bio_txt = self.add_emojis(self.bio.value)
        self.image_txt = self.image.value

        async def edit_intro(oldIntroMessage: discord.Message):
            embed = oldIntroMessage.embeds[0]
            await interaction.response.send_message("Your intro will be edited!", ephemeral=True)
            # check if the user's top role has changed (promotion/demotion)
            if (embed.footer.text == self.role.name) or (
                embed.footer.text == "Kurzgesagt Official" and self.role.id == Reference.Roles.kgsofficial
            ):
                newembed = self.create_embed()
                async with IntroLock.reorder_lock:
                    await oldIntroMessage.edit(embed=newembed)
            else:
                rolename = embed.footer.text
                oldrole = discord.utils.find(lambda role: role.name == rolename, self.kgs_guild.roles)
                if self.role > oldrole:
                    async with IntroLock.reorder_lock:
                        await self.reorder_promotion(oldIntroMessage)
                elif self.role < oldrole:
                    async with IntroLock.reorder_lock:
                        await self.reorder_demotion(oldIntroMessage)

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
            await interaction.response.send_message("Incorrect image link, please try again", ephemeral=True)
            return

        # check if the message was deleted for some reason
        if self.oldIntro:
            if not self.oldIntro["message_id"]:
                await interaction.response.send_message(
                    "Something went wrong, can't find the intro message. Do the intros have to be reorganized?",
                    ephemeral=True,
                )
                return
            try:
                oldIntroMessage = await self.intro_channel.fetch_message(self.oldIntro["message_id"])
                await edit_intro(oldIntroMessage)
                return
            except discord.NotFound:
                await interaction.response.send_message(
                    "Something went wrong, can't find the intro message. Do the intros have to be reorganized?",
                    ephemeral=True,
                )
                return

        await interaction.response.send_message("Your intro will be added!", ephemeral=True)
        async with IntroLock.reorder_lock:
            await self.reorder_add()


class IntroLock:
    reorder_lock = asyncio.Lock()
