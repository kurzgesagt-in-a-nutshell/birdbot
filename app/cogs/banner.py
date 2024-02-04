"""
banner.py

The banners that are stored within the mongo database are the image urls that
are sent in the banners_and_topics channel. If the reference to these are
removed then the urls are lost.

The banner suggest design goes as following:
User runs command to suggest photo. In this process an embed is created to
be displayed to the qualified users to accept or deny the suggested photo. A 
view is attached to the embed's message to enable the user input of accepting
or denying the photo. This view is a global view and therefore can be used
multiple times with different messages and listens to all active references of
it. 

Once the qualified user selects the action, the view is removed, the embed is
updated to display the chocie made and the banner is added or not.
"""

import io
import logging
import re
import typing

import aiohttp
import discord
from discord import Interaction, app_commands
from discord import ui as dui
from discord.ext import commands, tasks
from discord.interactions import Interaction
from pymongo.errors import CollectionInvalid

from app.birdbot import BirdBot
from app.utils import checks, errors
from app.utils.config import Reference
from app.utils.helper import BannerCycle, calc_time, get_time_string

if typing.TYPE_CHECKING:
    from pymongo.collection import Collection

logger = logging.getLogger(__name__)


class BannerView(dui.View):
    """
    The static view that is used for handling the controls of accepting or
    denying a banner suggestion
    """

    def __init__(self, banner_db, banners: list, accept_id: str, deny_id: str):
        super().__init__(timeout=None)

        self.banner_db: Collection = banner_db
        self.banners = banners

        self._accept.custom_id = accept_id
        self._deny.custom_id = deny_id

    def filename_from_url(self, url: str | None):
        # yes this only works for cdn.discordapp links
        if url:
            filename = url.split("/")[6].split("?")[0]
        else:
            filename = "banner.png"
        return filename

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Checks that the interactor is a moderator+ for the defined guild
        """

        guild = discord.utils.get(interaction.client.guilds, id=Reference.guild)

        assert guild
        assert interaction.guild
        assert isinstance(interaction.user, discord.Member)

        mod_role = guild.get_role(Reference.Roles.moderator)

        return interaction.guild.id == guild.id and interaction.user.top_role >= mod_role

    @dui.button(
        label="Accept",
        style=discord.ButtonStyle.blurple,
        emoji=discord.PartialEmoji.from_str(Reference.Emoji.PartialString.kgsYes),
    )
    async def _accept(self, interaction: Interaction, button: dui.Button):
        """
        Accepts the banner and removes the view from the message
        Changes the embed to indicate it was accepted and by who
        """
        message = interaction.message
        assert message

        embed = message.embeds[0]
        url = embed.image.url

        embed.title = f"Accepted by {interaction.user.name}"
        embed.colour = discord.Colour.green()

        # This is needed for discord to understand we are not trying to display
        # the file itself and the image in the embed. (duplicate images)

        filename = self.filename_from_url(url)
        embed.set_image(url=f"attachment://{filename}")

        self.banners.append(message.id)
        self.banner_db.update_one({"name": "banners_id"}, {"$set": {"banners": self.banners}})
        BannerCycle().queue_last(message.id)

        await interaction.response.edit_message(embed=embed, view=None)
        assert embed.author.name
        try:
            match = re.match(r".*\(([0-9]+)\)$", embed.author.name)
            if match:
                userid = match.group(1)
                suggester = await interaction.client.fetch_user(int(userid))
                await suggester.send(f"Your banner suggestion was accepted {url}")

        except discord.Forbidden:
            pass

    @dui.button(
        label="Deny",
        style=discord.ButtonStyle.danger,
        emoji=discord.PartialEmoji.from_str(Reference.Emoji.PartialString.kgsNo),
    )
    async def _deny(self, interaction: Interaction, button: dui.Button):
        """
        Denys the banner and removes the view from the message
        Changes the embed to indicate it was denied and by who
        """
        message = interaction.message
        assert message
        embed = message.embeds[0]

        embed.title = f"Denied by {interaction.user.name}"
        embed.colour = discord.Colour.red()

        # This is needed for discord to understand we are not trying to display
        # the file itself and the image in the embed. (duplicate images)

        filename = self.filename_from_url(embed.image.url)
        embed.set_image(url=f"attachment://{filename}")

        await interaction.response.edit_message(embed=embed, view=None)


class Banner(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.logger = logging.getLogger("Banners")
        self.bot = bot

        self.index = 0
        self.banner_db: Collection = self.bot.db.Banners

    async def cog_load(self) -> None:
        banners_find = self.banner_db.find_one({"name": "banners_id"})
        if banners_find == None:
            raise CollectionInvalid
        self.banners: typing.List = banners_find["banners"]
        self.banner_cycle = BannerCycle(self.banners)

        self.BANNER_ACCEPT = f"BANNER-ACCEPT-{self.bot._user().id}"
        self.BANNER_DENY = f"BANNER-DENY-{self.bot._user().id}"

        self.BANNER_VIEW = BannerView(
            banner_db=self.banner_db, banners=self.banners, accept_id=self.BANNER_ACCEPT, deny_id=self.BANNER_DENY
        )

        self.bot.add_view(self.BANNER_VIEW)

    async def cog_unload(self):
        self.timed_banner_rotation.cancel()
        self.BANNER_VIEW.stop()

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
                                return banner, response.content_type.split("/")[1]
                            return url, response.content_type.split("/")[1]
                        raise errors.InvalidParameterError(
                            content=f"Image must be less than 10240kb, yours is {int(len(banner)/1024)}kb."
                        )

                    raise errors.InvalidParameterError(
                        content=f"Link must be for an image file not {response.content_type}."
                    )

        except aiohttp.InvalidURL:
            raise errors.InvalidParameterError(content="The link provided is not valid")

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

        automated_channel = self.bot._get_channel(Reference.Channels.banners_and_topics)

        url_: bytes | str
        if url:
            url_, img_type = await self.verify_url(url=url, byte=True)
        elif image:
            url_, img_type = await self.verify_url(url=image.url, byte=True)
        else:
            raise errors.InvalidParameterError(content="An image file or url is required")

        file = discord.File(io.BytesIO(url_), filename=f"banner.{img_type}")  # type: ignore

        embed = discord.Embed(title="Banner Added", color=discord.Color.green())
        embed.set_author(
            name=interaction.user.name + "#" + interaction.user.discriminator,
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_image(url=f"attachment://banner.{img_type}")
        embed.set_footer(text="banner")

        # Uploads the information to the banners channel
        # The message ID is then extracted from this embed to keep a static reference
        # The message ID is later used to fetch the image
        message = await automated_channel.send(embed=embed, file=file)

        self.banners.append(message.id)
        self.banner_db.update_one({"name": "banners_id"}, {"$set": {"banners": self.banners}})
        BannerCycle().queue_last(message.id)

        await interaction.edit_original_response(content="Banner added.")

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
            return await interaction.response.send_message("Banner rotation stopped.", ephemeral=True)

        assert duration
        time, extra = calc_time([duration, ""])
        if time == 0:
            return await interaction.response.send_message("Wrong time syntax.", ephemeral=True)

        if not self.timed_banner_rotation.is_running():
            self.timed_banner_rotation.start()

        assert time
        self.timed_banner_rotation.change_interval(seconds=time)

        await interaction.response.send_message(f"Banners are rotating every {get_time_string(time)}.", ephemeral=True)

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

        automated_channel = self.bot._get_channel(Reference.Channels.banners_and_topics)

        url_: bytes | str
        if url:
            if not url.startswith("https://cdn.discordapp.com"):
                raise errors.InvalidParameterError(content="Only discord cdn links are supported")
            url_, img_type = await self.verify_url(url=url, byte=True)

        elif image:
            url_, img_type = await self.verify_url(url=image.url, byte=True)

        else:
            raise errors.InvalidParameterError(content="An image file or url is required")

        file = discord.File(io.BytesIO(url_), filename=f"banner.{img_type}")  # type: ignore

        embed = discord.Embed(color=0xC8A2C8)
        embed.set_author(
            name=f"{interaction.user.name} ({interaction.user.id})",
            icon_url=interaction.user.display_avatar.url,
        )
        embed.set_image(url=f"attachment://banner.{img_type}")
        embed.set_footer(text="banner")
        await automated_channel.send(embed=embed, file=file, view=self.BANNER_VIEW)

        await interaction.edit_original_response(content="Banner suggested.")

    @banner_commands.command()
    @checks.mod_and_above()
    @app_commands.checks.cooldown(1, 30, key=lambda i: (i.guild_id, i.user.id))
    async def change(
        self,
        interaction: discord.Interaction,
        image: typing.Optional[discord.Attachment] = None,
        url: typing.Optional[str] = None,
        queue: typing.Optional[bool] = False,
    ):
        """Change the current server banner

        Parameters
        ----------
        image: discord.Attachment
            An image file
        url: str
            URL or Link of an image
        queue: bool
            Queue this banner next in rotation
        """
        url_: str | bytes
        if url:
            url_, img_type = await self.verify_url(url=url, byte=not queue)

        elif image:
            url_, img_type = await self.verify_url(url=image.url, byte=not queue)

        else:
            raise errors.InvalidParameterError(content="An image file or url is required")

        if not queue:
            assert isinstance(url_, bytes)
            self.logger.info(f"Changed Banner to {url_}")
            await self.bot.get_mainguild().edit(banner=url_)
            await interaction.response.send_message("Server banner changed!", ephemeral=True)
        else:
            logger.info("Added banner to be queued next")
            BannerCycle().queue_next(url_)
            await interaction.response.send_message("Banner queued next", ephemeral=True)

    @tasks.loop()
    async def timed_banner_rotation(self):
        """
        Task that rotates the banner
        """
        guild = self.bot.get_mainguild()
        cur_banner_id = next(self.banner_cycle)
        self.logger.info(f"{cur_banner_id}")
        automated_channel = self.bot._get_channel(Reference.Channels.banners_and_topics)
        try:
            if type(cur_banner_id) is not str:
                message = await automated_channel.fetch_message(cur_banner_id)
                url = None
                if message.embeds:
                    url = message.embeds[0].image.url
                # this is necessary for legacy reasons
                elif message.attachments:
                    url = message.attachments[0].url
                if url is None:
                    raise commands.BadArgument()
            else:
                url = cur_banner_id
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    banner = await response.content.read()
                    await guild.edit(banner=banner)
                    self.logger.info(f"Rotated Banner {url}")
        except:
            logger.exception("Failed rotating banner")


async def setup(bot: BirdBot):
    await bot.add_cog(Banner(bot))
