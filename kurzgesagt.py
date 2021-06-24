import logging
import os
import time
from discord.ext.commands import errors
import dotenv

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
            super().__init__(command_prefix=["!", "k!"], case_insensitive=True,
                             owner_ids={389718094270038018, 183092910495891467}, reconnect=True,
                             activity=discord.Activity(type=discord.ActivityType.listening, name="to Steve's voice"))

        # This is a test string XDXD

        self.starttime = time.time()
        cogs = ['cogs.moderation', 'cogs.dev', 'cogs.help', 'cogs.fun']
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
        # TIMED
        await helper.start_timed_actions(self)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        if isinstance(error, commands.MissingPermissions):
            pass

        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send("Missing Arguments. Please check syntax using help command.")

        elif isinstance(error, commands.CommandNotFound):
            pass

        elif isinstance(error, commands.errors.CommandOnCooldown):
            return await ctx.send(error, delete_after=3.0)

        else:
            logger.error(str(error))
            return await ctx.send("Can't execute the command!!")


try:
    if args.beta:
        logger.info('Running beta instance')
        token = os.environ.get('BETA_BOT_TOKEN')
    else:
        token = os.environ.get('MAIN_BOT_TOKEN')
except KeyError:
    logger.error('No tokens found, check .env file')

Bot().run(token)
