import logging
import json
import typing
import aiohttp

import discord
from discord.ext import commands, tasks
from utils.helper import mod_and_above, calc_time, get_time_string


class Banner(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Banners')
        self.bot = bot

        banners = open('banners.json', 'r')
        self.banners = json.loads(banners.read())['banners']
        banners.close()

        config_file = open('config.json', 'r')
        config_json = json.loads(config_file.read())
        config_file.close()

        self.mod_role = config_json['roles']['mod_role']
        self.automated_channel = config_json['logging']['automated_channel']

        self.index = 0

    def cog_unload(self):
        self.timed_banner_rotation.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Banners')

    @commands.group(invoke_without_command=True)
    async def banner(self, ctx):
        """
            Banner commands
            Usage: banner < add | suggest | rotate | change >
        """
        pass

    async def verify_url(self, url, change=False):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.content_type.startswith("image"):
                        banner = await response.content.read()
                        if len(banner)/1024 < 10240:
                            if change:
                                return banner
                            return url
                        else:
                            raise commands.BadArgument(
                                message=f'Image must be less than 10240kb, yours is {int(len(banner)/1024)}kb.')
                    else:
                        raise commands.BadArgument(
                            message=f'Link must be for an image file not {response.content_type}.')
        except aiohttp.InvalidURL:
            raise commands.BadArgument(
                message="You must provide a link or an attachment.")

    @mod_and_above()
    @banner.command()
    async def add(self, ctx, url: typing.Optional[str] = None):
        """
            Add a banner by url or attachment
            Usage: banner add url or attachment
        """
        if url is None:
            attachments = ctx.message.attachments
            if attachments:
                url = attachments[0].url
            else:
                raise commands.BadArgument(
                    message=f'You must provide a url or attachment.'
                )

        self.banners.append(await self.verify_url(url))
        await ctx.send("Banner added!")
        banners = open('banners.json', 'w')
        banners.write(json.dumps({"banners": self.banners}, indent=4))
        banners.close()

    @mod_and_above()
    @banner.command()
    async def rotate(self, ctx, arg: str = None):
        """
            Change server banner rotation time or stop the rotation
            Usage: banner rotate time or stop
        """

        if arg is None:
            raise commands.BadArgument(
                message=f'You must provide rotation period or "stop" to stop rotation'
            )

        time, reason = calc_time([arg, ""])

        if reason == 'stop ':
            self.timed_banner_rotation.cancel()
            await ctx.message.delete(delay=6)
            await ctx.send("Banner rotation stopped.", delete_after=6)
            return
        elif time == None:
            raise commands.BadArgument(
                message="Wrong time syntax or did you mean to run rotate stop?")

        if not self.timed_banner_rotation.is_running():
            self.timed_banner_rotation.start()
        await ctx.message.delete(delay=6)
        self.timed_banner_rotation.change_interval(seconds=time)
        await ctx.send(f'Banners are rotating every {get_time_string(time)}.', delete_after=6)

    @banner.command()
    async def suggest(self, ctx, url: typing.Optional[str] = None):
        """
            Members can suggest banners to be reviewed by staff
            Usage: banner suggest url or attachment
        """
        automated_channel = self.bot.get_channel(self.automated_channel)

        embed = discord.Embed(title=f'{ctx.author.name} suggested')

        if url is None:
            attachments = ctx.message.attachments
            if attachments:
                url = attachments[0].url
            else:
                raise commands.BadArgument(
                    message="You must provide a url or attachment."
                )

        url = await self.verify_url(url)

        await ctx.send("Banner suggested.", delete_after=4)
        await ctx.message.delete(delay=4)

        embed.set_image(url=url)
        embed.set_footer(text="banner")
        message = await automated_channel.send(embed=embed)
        await message.add_reaction('<:kgsYes:580164400691019826>')
        await message.add_reaction('<:kgsNo:610542174127259688>')

    @mod_and_above()
    @banner.command()
    async def change(self, ctx, url: typing.Optional[str] = None):
        """
            Change the banner
            Usage: banner change url or attachment
        """
        if url is None:
            attachments = ctx.message.attachments
            if attachments:
                url = attachments[0].url
            else:
                raise commands.BadArgument(
                    message="You must provide a url or attachment."
                )

        banner = await self.verify_url(url, True)

        await ctx.message.delete(delay=4)
        await ctx.guild.edit(banner=banner)
        await ctx.send("Server banner changed!", delete_after=4)

    @tasks.loop()
    async def timed_banner_rotation(self):
        guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
        if self.index >= len(self.banners):
            self.index = 0
        async with aiohttp.ClientSession() as session:
            async with session.get(self.banners[self.index]) as response:
                banner = await response.content.read()
                await guild.edit(banner=banner)
                self.index += 1

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # User banner suggestions
        if payload.channel_id == self.automated_channel and not payload.member.bot:
            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            mod_role = guild.get_role(self.mod_role)
            if payload.member.top_role >= mod_role:
                message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                if message.embeds and message.embeds[0].footer.text == 'banner':
                    if payload.emoji.id == 580164400691019826:
                        url = message.embeds[0].image.url
                        self.banners.append(url)
                        banners = open('banners.json', 'w')
                        banners.write(json.dumps(
                            {"banners": self.banners}, indent=4))
                        banners.close()
                        embed = discord.Embed(
                            title="Banner added!", colour=discord.Colour.green())
                        embed.set_image(url=url)
                        await message.edit(embed=embed, delete_after=6)
                    elif payload.emoji.id == 610542174127259688:
                        embed = discord.Embed(
                            title="Banner suggestion removed!")
                        await message.edit(embed=embed, delete_after=6)


def setup(bot):
    bot.add_cog(Banner(bot))
