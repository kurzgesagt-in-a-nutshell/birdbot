import logging
import aiohttp
from bs4 import BeautifulSoup
import json
from random import randint
import time
import typing

import discord
from discord.ext import commands, tasks


class Smfeed(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Smfeed')
        self.bot = bot
        self.urls = {"https://www.youtube.com/c/KurzgesagtDE/videos": "", "https://www.youtube.com/c/kurzgesagtES/videos": ""}
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Smfeed')
        self.de_es_videos.start()
    
    async def new_video(self, url):
        """Returns the last video link on the channel provided by url"""

        cookies = {"CONSENT": f"YES+cb.20210813-05-p0.en-GB+FX+{randint(100,999)}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, cookies=cookies) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                allscript = soup.find_all("script")
                
                videos = allscript[32].contents[0]
                videos = str(videos)
                video = json.loads(videos[20:-1])

                return "https://www.youtube.com/watch?v="+video["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][1]["tabRenderer"]["content"]["sectionListRenderer"]["contents"][0]["itemSectionRenderer"]["contents"][0]["gridRenderer"]["items"][0]["gridVideoRenderer"]["videoId"]


    @commands.command()
    async def en_video(self, ctx, tim: typing.Optional[int] = 5):
        """Command description"""
        url = "https://www.youtube.com/c/inanutshell/videos"
        prev_vid = await self.new_video(url)
        await ctx.send(f"Scraping started for {tim} seconds")
        a=0
        end = time.time() + tim
        while time.time() < end:
            last_vid = await self.new_video(url)
            a+=1
            if last_vid != prev_vid:
                await ctx.send(last_vid)
                break
            pass
        await ctx.send(f"Scraping ended {a}")

    @tasks.loop(minutes=10)
    async def de_es_videos(self):
        """Every 10 minutes check for a new spanish and german video"""

        for url in self.urls:
            last_vid = await self.new_video(url)
            
            if self.urls[url] == "":
                self.urls[url] = last_vid

            if last_vid == self.urls[url]:
                pass
            else:
                self.urls[url] = last_vid
                channel = self.bot.get_channel(414179142020366336)
                await channel.send(last_vid)


def setup(bot):
    bot.add_cog(Smfeed(bot))

