import logging
import aiohttp
from bs4 import BeautifulSoup
import json
from random import randint
import time
import typing

import discord
from discord.ext import commands, tasks
from utils.helper import mod_and_above


class Smfeed(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Smfeed")
        self.bot = bot
        # youtube channel: ["last video url", channel id, role id]
        self.urls = {
            "https://www.youtube.com/c/KurzgesagtDE/videos": [
                "",
                769596357329158204,
                642097150158962688,
            ],
            "https://www.youtube.com/c/kurzgesagtES/videos": [
                "",
                769596474014564393,
                677171902397284363,
            ],
        }

        with open("config.json", "r") as config_file:
            config_json = json.loads(config_file.read())

        self.mod_role = config_json["roles"]["mod_role"]
        self.automated_channel = config_json["logging"]["automated_channel"]

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Smfeed")
        self.de_es_videos.start()

    async def new_video(self, url):
        """Returns the last video link on the channel provided by url"""

        cookies = {"CONSENT": f"YES+cb.20210813-05-p0.en-GB+FX+{randint(100,999)}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, cookies=cookies) as response:
                html = await response.text()
                soup = BeautifulSoup(html, "lxml")
                allscript = soup.find_all("script")

                videos = allscript[32].contents[0]
                videos = str(videos)
                video = json.loads(videos[20:-1])

                return (
                    "https://www.youtube.com/watch?v="
                    + video["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][1][
                        "tabRenderer"
                    ]["content"]["sectionListRenderer"]["contents"][0][
                        "itemSectionRenderer"
                    ][
                        "contents"
                    ][
                        0
                    ][
                        "gridRenderer"
                    ][
                        "items"
                    ][
                        0
                    ][
                        "gridVideoRenderer"
                    ][
                        "videoId"
                    ]
                )

    @mod_and_above
    @commands.command()
    async def en_video(self, ctx, tim: typing.Optional[int] = 5):
        """
        Repeatedly scrapes for new videos on the english channel
        usage: en_video time
        """
        url = "https://www.youtube.com/c/inanutshell/videos"
        prev_vid = await self.new_video(url)
        await ctx.send(f"Scraping started for {tim} seconds")
        a = 0
        end = time.time() + tim
        while time.time() < end:
            last_vid = await self.new_video(url)
            a += 1
            if last_vid != prev_vid:
                await ctx.send(last_vid)
                channel = self.bot.get_channel(540872295279755275)
                await channel.send(f"{last_vid}\n@everyone")
                break
            pass
        await ctx.send(f"Scraping ended {a}")

    @tasks.loop(minutes=10)
    async def de_es_videos(self):
        """Every 10 minutes check for a new spanish and german video"""

        for url in self.urls:
            last_vid = await self.new_video(url)

            if self.urls[url][0] == "":
                self.urls[url][0] = last_vid

            if last_vid == self.urls[url][0]:
                pass
            else:
                self.urls[url][0] = last_vid
                channel = self.bot.get_channel(self.urls[url][1])
                guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
                role = guild.get_role(self.urls[url][2])
                await channel.send(f"{last_vid}\n{role.mention}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """React to the twitter webhooks"""
        if message.channel.id == 580354435302031360:
            await message.add_reaction("<:kgsThis:567150184853798912>")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """If mod or above reacts to twitter webhook post tweet to proper channel"""
        if (
            payload.channel_id == 580354435302031360
            and not payload.member.bot
            and payload.emoji.id == 567150184853798912
        ):
            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            mod_role = guild.get_role(self.mod_role)
            if payload.member.top_role >= mod_role:
                channel = self.bot.get_channel(489450008643502080)
                message = await channel.fetch_message(payload.message_id)
                await channel.send(message.content)


def setup(bot):
    bot.add_cog(Smfeed(bot))
