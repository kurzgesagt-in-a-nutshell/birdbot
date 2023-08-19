import logging
import json
import typing
import aiohttp

import io

import discord
from discord.ext import commands, tasks
from discord import app_commands

from app.utils import checks
from app.utils.helper import (
    calc_time,
    get_time_string,
)

from app.utils.config import Reference

class Banner(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Banners")
        self.bot = bot

        self.index = 0
        self.banner_db = self.bot.db.Banners

    def cog_load(self) -> None:
        self.banners = self.banner_db.find_one({"name": "banners"})["banners"]

    def cog_unload(self):
        self.timed_banner_rotation.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Banners")

    banner_commands = app_commands.Group(
        name="banner",
        description="Guild banner commands",
        guild_ids=[Reference.guild],
        default_permissions=discord.permissions.Permissions(manage_messages=True),
    )

    async def verify_url(self, url: str, byte: bool = False):
        """
        returns url after verifyng size and content_type
        returns bytes object if byte is set to True
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.content_type.startswith("image"):
                        banner = await response.content.read()

                        if len(banner) / 1024 < 10240:
                            if byte:
                                return banner
                            return url
                        raise commands.BadArgument(
                            message=f"Image must be less than 10240kb, yours is {int(len(banner)/1024)}kb."
                        )

                    raise commands.BadArgument(
                        message=f"Link must be for an image file not {response.content_type}."
                    )

        except aiohttp.InvalidURL:
            raise commands.BadArgument(
                message="You must provide a link or an attachment."
            )

    @banner_commands.command()
    @checks.mod_and_above()
    async def add(
        self,
        interaction: discord.Interaction,
        image: typing.Optional[discord.Attachment] = None,
        url: typing.Optional[str] = None,
    ):
        """Add or upload a banner

        Parameters
        ----------
        image: discord.Attachment
            An image file
        url: str
            URL or Link of an image
        """

        await interaction.response.defer(ephemeral=True)

        if image:

            try:
                fp = await self.verify_url(url=image.url, byte=True)
            except commands.BadArgument as ba:
                return await interaction.edit_original_response(content=str(ba))
            except Exception as e:
                raise e

            if fp:
                banners_channel = interaction.guild.get_channel(Reference.Channels.banners_and_topics)
                msg = await banners_channel.send(
                    file=discord.File(io.BytesIO(fp), filename=image.filename)
                )

                url = msg.attachments[0].url

        elif url:
            try:
                url = await self.verify_url(url=url)
            except commands.BadArgument as ba:
                return await interaction.edit_original_response(content=str(ba))
            except Exception as e:
                raise e

        else:
            return await interaction.edit_original_response(
                content="Required any one of the parameters."
            )

        self.banners.append(url)

        self.banner_db.update_one(
            {"name": "banners"}, {"$set": {"banners": self.banners}}
        )
        await interaction.edit_original_response(content="Banner added successfully.")

    @banner_commands.command()
    @checks.mod_and_above()
    async def rotate(
        self,
        interaction: discord.Interaction,
        duration: typing.Optional[str] = None,
        stop: typing.Optional[bool] = False,
    ):
        """Change server banner rotation duration or stop the rotation

        Parameters
        ----------
        duration: str
            Time (example: 3hr or 1d)
        stop: bool
            Weather to stop banner rotation
        """

        if not stop and not duration:
            return await interaction.response.send_message(
                "Please provide value for atleast one argument.", ephemeral=True
            )

        if stop:
            self.timed_banner_rotation.cancel()
            return await interaction.response.send_message(
                "Banner rotation stopped.", ephemeral=True
            )

        time, extra = calc_time([duration, ""])
        if time == 0:
            return await interaction.response.send_message(
                "Wrong time syntax.", ephemeral=True
            )

        if not self.timed_banner_rotation.is_running():
            self.timed_banner_rotation.start()

        self.timed_banner_rotation.change_interval(seconds=time)
        await interaction.response.send_message(
            f"Banners are rotating every {get_time_string(time)}.", ephemeral=True
        )

    # Making this standalone command cause can not override default permissions, and we need only this command to be visible to users.
    @app_commands.command()
    @app_commands.default_permissions(send_messages=True)
    @app_commands.guilds(Reference.guild)
    @app_commands.checks.cooldown(1, 60, key=lambda i: (i.guild_id, i.user.id))
    async def banner_suggest(
        self,
        interaction: discord.Interaction,
        image: typing.Optional[discord.Attachment] = None,
        url: typing.Optional[str] = None,
    ):
        """Suggest an image from kurzgesagt for server banner

        Parameters
        ----------
        image: discord.Attachment
            An image file
        url: str
            URL or Link of an image
        """
        await interaction.response.defer(ephemeral=True)
        automated_channel = interaction.guild.get_channel(Reference.Channels.banners_and_topics)

        if image:
            try:
                url = await self.verify_url(url=image.url, byte=True)
            except commands.BadArgument as ba:
                return await interaction.edit_original_response(content=str(ba))
            except Exception as e:
                raise e

        elif url:
            try:
                url = await self.verify_url(url=url, byte=True)
            except commands.BadArgument as ba:
                return await interaction.edit_original_response(content=str(ba))
            except Exception as e:
                raise e

        else:
            return await interaction.edit_original_response(
                content="Required any one of the parameters."
            )

        file = discord.File(io.BytesIO(url), filename="banner.png")

        embed = discord.Embed(color=0xC8A2C8)
        embed.set_author(
            name=interaction.user.name + "#" + interaction.user.discriminator,
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_image(url="attachment://banner.png")
        embed.set_footer(text="banner")
        message = await automated_channel.send(embed=embed, file=file)
        await message.add_reaction("<:kgsYes:955703069516128307>")
        await message.add_reaction("<:kgsNo:955703108565098496>")

        await interaction.edit_original_response(content="Banner suggested.")

    @banner_commands.command()
    @checks.mod_and_above()
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def change(
        self,
        interaction: discord.Interaction,
        image: typing.Optional[discord.Attachment] = None,
        url: typing.Optional[str] = None,
    ):
        """Change server banner

        Parameters
        ----------
        image: discord.Attachment
            An image file
        url: str
            URL or Link of an image
        """
        if url is None:
            if image:
                url = image.url
            else:
                return await interaction.response.send_message(
                    "You must provide a url or attachment.", ephemeral=True
                )

        try:
            banner = await self.verify_url(url, byte=True)
        except commands.BadArgument as ba:
            return await interaction.response.send_message(str(ba), ephemeral=True)
        except Exception as e:
            raise e

        await interaction.guild.edit(banner=banner)

        await interaction.response.send_message(
            "Server banner changed!", ephemeral=True
        )

    @tasks.loop()
    async def timed_banner_rotation(self):
        """
        Task that rotates the banner
        """
        guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
        if self.index >= len(self.banners):
            self.index = 0
        async with aiohttp.ClientSession() as session:
            async with session.get(self.banners[self.index]) as response:
                banner = await response.content.read()
                await guild.edit(banner=banner)
                self.index += 1

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """
        Check if reaction added is by mod+ and approve/deny banner accordingly
        """
        if payload.channel_id == Reference.Channels.banners_and_topics and not payload.member.bot:
            guild = discord.utils.get(self.bot.guilds, id=Reference.guild)
            mod_role = guild.get_role(Reference.Roles.moderator)

            if payload.member.top_role >= mod_role:
                message = await self.bot.get_channel(payload.channel_id).fetch_message(
                    payload.message_id
                )

                if message.embeds and message.embeds[0].footer.text == "banner":
                    if payload.emoji.id == Reference.Emoji.kgsYes:
                        url = message.embeds[0].image.url
                        author = message.embeds[0].author
                        embed = discord.Embed(colour=discord.Colour.green())
                        embed.set_image(url=url)
                        embed.set_author(name=author.name, icon_url=author.icon_url)

                        image = await self.verify_url(url, byte=True)
                        channel = self.bot.get_channel(Reference.Channels.banners_and_topics)
                        file = discord.File(io.BytesIO(image), filename="banner.png")
                        banner = await channel.send(file=file)
                        url = banner.attachments[0].url
                        self.banners.append(url)
                        self.banner_db.update_one(
                            {"name": "banners"}, {"$set": {"banners": self.banners}}
                        )

                        await message.edit(embed=embed, delete_after=6)
                        member = guild.get_member_named(author.name)
                        try:
                            await member.send(
                                f"Your banner suggestion was accepted {url}"
                            )
                        except discord.Forbidden:
                            pass

                    elif payload.emoji.id == Reference.Emoji.kgsNo:  # kgsNo emoji
                        embed = discord.Embed(title="Banner suggestion removed!")
                        await message.edit(embed=embed, delete_after=6)


async def setup(bot):
    await bot.add_cog(Banner(bot))
