import logging
import json
import typing
import aiohttp
from utils import helper

import discord
from discord.ext import commands, tasks


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
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Banners')
    
    @commands.command()
    async def add_banner(self, ctx, url: typing.Optional[str]):
        """Add a banner by url or attachment"""
        if url == None:
            attachments = ctx.message.attachments
            if attachments != []:
                if attachments[0].content_type[:5] == "image":
                    self.banners.append(attachments[0].url)
        else:
            self.banners.append(url)

        await ctx.send("Banner added!")

        banners = open('banners.json', 'w')
        banners.write(json.dumps({"banners": self.banners}, indent=4))
        banners.close()

    @commands.command()
    async def rotate_banner(self, ctx, *, time:int):
        """Command description"""
        #tot_time_s = helper.calc_time(time.split(" "))[0]
        await ctx.send(f'{time} minutes')
        self.time = time
        self.timed_action_loop.start()
    
    @tasks.loop(minutes=1.0)
    async def timed_action_loop(self):
        guild = discord.utils.get(self.bot.guilds, id=414027124836532234)

        if self.index <= len(self.banners):
            async with aiohttp.ClientSession() as session:
                print(self.index)
                async with session.get(self.banners[self.index]) as response:
                    banner = await response.content.read()
                    print(self.index)
                    await guild.edit(banner=banner)
                    self.index += 1
        else:
            self.index = 0


    @commands.command()
    async def suggest_banner(self, ctx, url: typing.Optional[str]):
        """Members can suggest banners to be reviewed by staff"""
        automated_channel = self.bot.get_channel(self.automated_channel)

        embed = discord.Embed(title=f'{ctx.author.name} suggested')

        if url == None:
            attachments = ctx.message.attachments
            if attachments != []:
                if attachments[0].content_type[:5] == "image":
                    embed.set_image(url=attachments[0].url)
                    embed.set_footer(text="banner")
                    message = await automated_channel.send(embed=embed)
                    await message.add_reaction('<:kgsYes:580164400691019826>')
                    await message.add_reaction('<:kgsNo:610542174127259688>')
        else:
            embed.set_image(url=url)
            embed.set_footer(text="banner")
            message = await automated_channel.send(embed=embed)
            await message.add_reaction('<:kgsYes:580164400691019826>')
            await message.add_reaction('<:kgsNo:610542174127259688>')

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
    
    @commands.command()
    async def change_banner(self, ctx, url: typing.Optional[str]):
        """Change the banner"""
        if url == None:
            attachment = ctx.message.attachments
            if attachment != []:
                if attachment[0][:5] == "image":
                    url=attachment.url

        async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    banner = await response.content.read()
                    if len(banner)/1024 < 10240:
                        await ctx.guild.edit(banner=banner)
                    else:
                        raise commands.BadArgument(message=f'Image must be less than 10240kb, yours is {int(len(banner)/1024)}kb.')


def setup(bot):
    bot.add_cog(Banners(bot))

