import logging
import json
import typing
import aiohttp

import io

import discord
from discord.ext import commands, tasks
from utils.helper import (
    devs_only,
    mod_and_above,
    calc_time,
    get_time_string,
    bot_commands_only,
)


class Banner(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Banners")
        self.bot = bot

        with open("config.json", "r") as config_file:
            config_json = json.loads(config_file.read())

        self.mod_role = config_json["roles"]["mod_role"]
        self.automated_channel = config_json["logging"]["automated_channel"]

        self.index = 0
        self.banner_db = self.bot.db.Banners

    def cog_unload(self):
        self.timed_banner_rotation.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Banners")

        self.banners = self.banner_db.find_one({"name": "banners"})["banners"]

    @commands.group(hidden=True)
    async def banner(self, ctx: commands.Context):
        """
        Banner commands
        Usage: banner add/suggest/rotate/change
        """

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

    @mod_and_above()
    @banner.command()
    async def add(self, ctx: commands.context, *, url: str = None):
        """
        Add a banner by url or attachment
        Usage: banner add url/attachment
        """
        if url is None:
            attachments = ctx.message.attachments
            if attachments:
                url = [attachments[n].url for n, _ in enumerate(attachments)]
            else:
                raise commands.BadArgument(
                    message="You must provide a url or attachment."
                )
        else:
            url = url.split(" ")

        for i in url:
            self.banners.append(await self.verify_url(i))

        self.banner_db.update_one(
            {"name": "banners"}, {"$set": {"banners": self.banners}}
        )

        await ctx.send("Banner added!")

    @mod_and_above()
    @banner.command()
    async def rotate(self, ctx: commands.Context, arg: str = None):
        """
        Change server banner rotation time or stop the rotation
        Usage: banner rotate time/stop
        """

        if arg is None:
            raise commands.BadArgument(
                message='You must provide rotation period or "stop" to stop rotation'
            )

        time, reason = calc_time([arg, ""])

        if reason == "stop ":
            self.timed_banner_rotation.cancel()
            await ctx.message.delete(delay=6)
            await ctx.send("Banner rotation stopped.", delete_after=6)
            return
        if time is None:
            raise commands.BadArgument(
                message="Wrong time syntax or did you mean to run rotate stop?"
            )

        if not self.timed_banner_rotation.is_running():
            self.timed_banner_rotation.start()

        await ctx.message.delete(delay=6)
        self.timed_banner_rotation.change_interval(seconds=time)
        await ctx.send(
            f"Banners are rotating every {get_time_string(time)}.", delete_after=6
        )

    @banner.command()
    @bot_commands_only()
    async def suggest(self, ctx: commands.Context, url: typing.Optional[str] = None):
        """
        Members can suggest banners to be reviewed by staff
        Usage: banner suggest url/attachment
        """
        automated_channel = self.bot.get_channel(self.automated_channel)

        if url is None:
            attachments = ctx.message.attachments
            if attachments:
                url = attachments[0].url
            else:
                raise commands.BadArgument(
                    message="You must provide a url or attachment."
                )

        url = await self.verify_url(url, byte=True)

        file = discord.File(io.BytesIO(url), filename="banner.png")

        embed = discord.Embed(color=0xC8A2C8)
        embed.set_author(
            name=ctx.author.name + "#" + ctx.author.discriminator,
            icon_url=ctx.author.avatar_url,
        )
        embed.set_image(url="attachment://banner.png")
        embed.set_footer(text="banner")
        message = await automated_channel.send(embed=embed, file=file)
        await message.add_reaction("<:kgsYes:955703069516128307>")
        await message.add_reaction("<:kgsNo:955703108565098496>")

        await ctx.send("Banner suggested.", delete_after=4)
        await ctx.message.delete(delay=4)

    @mod_and_above()
    @banner.command()
    async def change(self, ctx: commands.Context, url: typing.Optional[str] = None):
        """
        Change the banner
        Usage: banner change url/attachment
        """
        if url is None:
            attachments = ctx.message.attachments
            if attachments:
                url = attachments[0].url
            else:
                raise commands.BadArgument(
                    message="You must provide a url or attachment."
                )

        banner = await self.verify_url(url, byte=True)

        await ctx.message.delete(delay=4)
        await ctx.guild.edit(banner=banner)
        await ctx.send("Server banner changed!", delete_after=4)

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
        if payload.channel_id == self.automated_channel and not payload.member.bot:
            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            mod_role = guild.get_role(self.mod_role)

            if payload.member.top_role >= mod_role:
                message = await self.bot.get_channel(payload.channel_id).fetch_message(
                    payload.message_id
                )

                if message.embeds and message.embeds[0].footer.text == "banner":
                    if payload.emoji.id == 955703069516128307:  # kgsYes emote
                        url = message.embeds[0].image.url
                        author = message.embeds[0].author
                        embed = discord.Embed(colour=discord.Colour.green())
                        embed.set_image(url=url)
                        embed.set_author(name=author.name, icon_url=author.icon_url)

                        image = await self.verify_url(url, byte=True)
                        channel = self.bot.get_channel(414179142020366336)
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

                    elif payload.emoji.id == 955703108565098496:  # kgsNo emoji
                        embed = discord.Embed(title="Banner suggestion removed!")
                        await message.edit(embed=embed, delete_after=6)


def setup(bot):
    bot.add_cog(Banner(bot))
