import logging
import os
import time
import dotenv

import discord
from discord.ext import commands
from rich.logging import RichHandler

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

        self.logger = logging.getLogger(__name__)

        try:
            del os.environ['FORCIBLY_KILLED']
        except KeyError:
            pass
        self.starttime = time.time()
        cogs = ['cogs.moderation', 'cogs.dev', 'cogs.help',
                'cogs.fun', 'cogs.global_listeners, cogs.filter']
        fails = {}
        for i in cogs:
            try:
                super().load_extension(i)
                self.logger.info(f'Loading {i}')
            except Exception as e:
                self.logger.exception(f'Exception at {i}')
                fails[i] = e

    async def on_ready(self):
        self.logger.info('Logged in as')
        self.logger.info(f"\tUser: {self.user.name}")
        self.logger.info(f"\tID  : {self.user.id}")
        self.logger.info('------')


def main():
    logger = logging.getLogger(__name__)
    logger.info("Delaying bot for server creation")
    time.sleep(5)

    try:
        if args.beta:
            logger.info('Running beta instance')
            token = os.environ.get('BETA_BOT_TOKEN')
        else:
            token = os.environ.get('MAIN_BOT_TOKEN')

        # run the bot
        Bot().run(token)

    except KeyError:
        logger.error('No tokens found, check .env file')


if __name__ == '__main__':
    main()
