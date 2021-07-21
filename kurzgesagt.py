import logging
import os
import time
import dotenv

import cProfile, pstats

import discord
from discord.ext import commands
from rich.logging import RichHandler

import helper
from loglevels import setup as llsetup

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-b", "--beta", help="Run the beta instance of the bot",
                    action="store_true")
args = parser.parse_args()

llsetup()
dotenv.load_dotenv()

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    handlers=[RichHandler()]
)

logger = logging.getLogger(__name__)
logger.info("Delaying bot for server creation")
time.sleep(5)


class Bot(commands.AutoShardedBot):
    """Main Bot"""

    def __init__(self):
        if args.beta:
            intents = discord.Intents.all()
            super().__init__(command_prefix="kt!", case_insensitive=True,
                             owner_ids={389718094270038018, 183092910495891467}, reconnect=True, intents=intents,
                             activity=discord.Activity(type=discord.ActivityType.watching, name="for bugs"))
        else:
            intents = discord.Intents.all()
            super().__init__(command_prefix=["!", "k!"], case_insensitive=True,
                             owner_ids={389718094270038018, 183092910495891467}, reconnect=True, intents=intents,
                             activity=discord.Activity(type=discord.ActivityType.listening, name="Steve's voice"))

        try:
            del os.environ['FORCIBLY_KILLED']
        except KeyError:
            pass
        self.starttime = time.time()
        cogs = ['cogs.moderation', 'cogs.dev', 'cogs.help',
                'cogs.fun', 'cogs.global_listeners']
        fails = {}
        for i in cogs:
            try:
                super().load_extension(i)
                logger.info(f'Loading {i}')
            except Exception as e:
                logger.exception(f'Exception at {i}')
                fails[i] = e

    async def on_ready(self):
        logger.info('Logged in as')
        logger.info(f"\tUser: {self.user.name}")
        logger.info(f"\tID  : {self.user.id}")
        logger.info('------')


try:
    if args.beta:
        logger.info('Running beta instance')
        token = os.environ.get('BETA_BOT_TOKEN')
    else:
        token = os.environ.get('MAIN_BOT_TOKEN')
except KeyError:
    logger.error('No tokens found, check .env file')

Bot().run(token)
