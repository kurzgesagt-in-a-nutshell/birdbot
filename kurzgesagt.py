import time
import os
import logging
import discord

from loglevels import setup as llsetup
from rich.logging import RichHandler
from discord.ext import commands

llsetup()

logging.basicConfig(
        format = "%(message)s",
        level = logging.INFO,
        handlers = [RichHandler()]
        )
logger = logging.getLogger(__name__)
print("Delaying bot for server creation")
time.sleep(5)
class Bot(commands.AutoShardedBot):
    """Main Bot"""

    def __init__(self):
        super().__init__(command_prefix="k!!",case_insensitive=True,owner_ids={389718094270038018,183092910495891467,424843380342784011},reconnect=True)
        self.starttime = time.time()
        cogs = ['cogs.moderation','cogs.dev']        
        fails = {}
        for i in cogs:
            try:
                super().load_extension(i)
                logger.info(f'Loading {i}')
            except Exception as e:
                logger.exception('Exception at {i}')
                fails[i] = e

    async def on_ready(self):
        logger.info('Logged in as')
        logger.info(f"\tUser: {self.user.name}")
        logger.info(f"\tID  : {self.user.id}")
        logger.info('------')
        # bot status
        activity = discord.Activity(type=discord.ActivityType.listening, name="Steve's voice" )
        await self.change_presence(activity = activity)


with open('token.txt') as tokenfile:
    token = tokenfile.read()


Bot().run(token)
