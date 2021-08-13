import logging
import json
import typing
import aiohttp

import discord
from discord import activity
from discord.ext import commands, tasks
from utils.helper import mod_and_above

class Banners(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Banners')
        self.bot = bot

        banners = open('banners.json', 'r')
        self.banners = json.loads(banners.read())['banners']
        banners.close()

        config_file = open('config.json', 'r')
        self.config_json = json.loads(config_file.read())
        config_file.close()

        self.automated_channel = self.config_json['logging']['automated_channel']

        self.index = 0

    
    def cog_unload(self):
        self.timed_banner_rotation.cancel()
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Banners')
    
    @commands.group()
    async def banner(self, ctx):
        """Banner commands"""
        pass
    
    #@mod_and_above()
    @banner.command()
    async def add(self, ctx, url: typing.Optional[str]):
        """Add a banner by url or attachment"""
        if url == None:
            attachments = ctx.message.attachments
            if attachments != []:
                url = attachments[0].url
        try:
            async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.content_type.startswith("image"):
                            banner = await response.content.read()
                            if len(banner)/1024 < 10240:
                                self.banners.append(url)
                                await ctx.send("Banner added!")
                                banners = open('banners.json', 'w')
                                banners.write(json.dumps({"banners": self.banners}, indent=4))
                                banners.close()
                            else:
                                raise commands.BadArgument(message=f'Image must be less than 10240kb, yours is {int(len(banner)/1024)}kb.')
                        else:
                            raise commands.BadArgument(message=f'Link must be for an image file not {response.content_type}')
        except aiohttp.InvalidURL:
            raise commands.BadArgument(message="You must provide a link or an attachment")

    #@mod_and_above()
    @banner.command()
    async def rotate(self, ctx, time:str):
        """Command description"""
        if time == 'stop':
            self.timed_banner_rotation.stop()
            await ctx.message.delete(delay=6)
            await ctx.send("Banner rotation stopped", delete_after=6)
            return
        elif time[-1] == 'd':
            time = int(time[:-1])*60*24
        elif time[-1] == 'h':
            time = int(time[:-1])*60
        elif time[-1] == 'm':
            time = int(time[:-1])
        else:
            raise commands.BadArgument(message="Time must be in the format 10d, 10h or 10m")
        if not self.timed_banner_rotation.is_running():
            self.timed_banner_rotation.start()
        await ctx.send(f'Banners are rotating every {time} minutes', delete_after=6)
        await ctx.message.delete(delay=6)
        self.timed_banner_rotation.change_interval(minutes=time)

    @banner.command()
    async def suggest(self, ctx, url: typing.Optional[str]):
        """Members can suggest banners to be reviewed by staff"""
        automated_channel = self.bot.get_channel(self.automated_channel)

        embed = discord.Embed(title=f'{ctx.author.name} suggested')

        if url == None:
            attachments = ctx.message.attachments
            if attachments != []:
                url = attachments[0].url

        try:            
            async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.content_type.startswith("image"):
                            banner = await response.content.read()
                            if len(banner)/1024 < 10240:
                                self.banners.append(url)
                                banners = open('banners.json', 'w')
                                banners.write(json.dumps({"banners": self.banners}, indent=4))
                                banners.close()
                                embed.set_image(url=url)
                                embed.set_footer(text="banner")
                                message = await automated_channel.send(embed=embed)
                                await message.add_reaction('<:kgsYes:580164400691019826>')
                                await message.add_reaction('<:kgsNo:610542174127259688>')
                            else:
                                raise commands.BadArgument(message=f'Image must be less than 10240kb, yours is {int(len(banner)/1024)}kb.')
                        else:
                            raise commands.BadArgument(message=f'Link must be for an image file not {response.content_type}')
        except aiohttp.InvalidURL:
            raise commands.BadArgument(message="You must provide a link or an attachment")
 
    #@mod_and_above()
    @banner.command()
    async def change(self, ctx, url: typing.Optional[str]):
        """Change the banner"""
        if url == None:
            attachment = ctx.message.attachments
            if attachment != []:
                url=attachment.url
        try:
            async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        banner = await response.content.read()
                        if len(banner)/1024 < 10240:
                            await ctx.guild.edit(banner=banner)
                        else:
                            raise commands.BadArgument(message=f'Image must be less than 10240kb, yours is {int(len(banner)/1024)}kb.')
        except aiohttp.InvalidURL:
            raise commands.BadArgument(message="You must provide a link or an attachment")

    @tasks.loop()
    async def timed_banner_rotation(self):
        guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
        if self.index == len(self.banners):
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
            message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
            if message.embeds[0].footer.text == 'banner':
                if payload.emoji.id == 580164400691019826:
                    url = message.embeds[0].image.url
                    self.banners.append(url)
                    banners = open('banners.json', 'w')
                    banners.write(json.dumps({"banners": self.banners}, indent=4))
                    banners.close()
                    embed = discord.Embed(title="Banner added!", colour=discord.Colour.green())
                    embed.set_image(url=url)
                    await message.edit(embed=embed, delete_after=6)
                elif payload.emoji.id == 610542174127259688:
                    embed = discord.Embed(title="Banner suggestion removed!")
                    await message.edit(embed=embed, delete_after=6)


def setup(bot):
    bot.add_cog(Banners(bot))
