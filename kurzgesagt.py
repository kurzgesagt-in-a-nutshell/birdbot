import logging
import asyncio
import os
import time
from contextlib import contextmanager
from logging.handlers import TimedRotatingFileHandler

import discord
import dotenv
from discord.ext import commands
from rich.logging import RichHandler


class StartupError(Exception):
    """Exception class for startup errors."""
    def __init__(self, base: Exception):
        super().__init__()
        self.exception = base


@contextmanager
def setup():
    try:
        dotenv.load_dotenv()
        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.INFO)

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        dtfmt = '%Y-%m-%d %H:%M:%S'
        handlers = [
            RichHandler(rich_tracebacks=True),
            TimedRotatingFileHandler(filename='birdbot.log', when='1M')
        ]
        fmt = logging.Formatter(
            '[{asctime}] [{levelname:<7}] {name}: {message}', dtfmt, style='{')

        for handler in handlers:
            logger.addHandler(handler)
            handler.setFormatter(fmt)

        yield
    finally:
        handlers = logger.handlers[:]
        for handler in handlers:
            handler.close()
            logger.removeHandler(handler)


class BirdBot(commands.AutoShardedBot):
    """Main Bot"""
    def __init__(self):
        self.db = self.get_database()

        self.logger = logging.getLogger(__name__)

        try:
            del os.environ['FORCIBLY_KILLED']
        except KeyError:
            pass
        self.starttime = time.time()
        cogs = [
            'cogs.moderation', 'cogs.dev', 'cogs.help', 'cogs.fun',
            'cogs.global_listeners'
        ]
        fails = {}
        for i in cogs:
            try:
                super().load_extension(i)
                self.logger.info(f'Loading {i}')
            except Exception as e:
                self.logger.exception(f'Exception at {i}')
                fails[i] = e

    @classmethod
    def from_parseargs(cls, args) -> "Bot":
        """Create and return an instance of a Bot."""
        allowed_mentions = discord.AllowedMentions(roles=False,
                                                   everyone=False,
                                                   users=True)
        loop = asyncio.get_event_loop()
        intents = discord.Intents(guilds=True,
                                  members=True,
                                  bans=True,
                                  emojis=True,
                                  webhooks=True,
                                  messages=True,
                                  reactions=True)
        if args.beta:
            prefix = "b!"
            owner_ids = {
                389718094270038018,  #FC
                424843380342784011,  #Oeav
                248790213386567680,  #Austin
                183092910495891467  #Sloth
            }
            activity = discord.Activity(type=discord.ActivityType.watching,
                                        name="for bugs")
        if args.alpha:
            prefix = "a!"
            owner_ids = {
                389718094270038018,  #FC
                424843380342784011,  #Oeav
                248790213386567680,  #Austin
                183092910495891467  #Sloth
            }
            activity = discord.Activity(type=discord.ActivityType.playing,
                                        name="imagine being a beta")
        else:
            prefix = "!"
            owner_ids = {183092910495891467}  #Sloth
            activity = discord.Activity(type=discord.ActivityType.listening,
                                        name="Steve's voice")
        return cls(loop=loop,
                   command_prefix=commands.when_mentioned_or(prefix),
                   owner_ids=owner_ids,
                   activity=activity,
                   case_insensitive=True,
                   allowed_mentions=allowed_mentions,
                   intents=intents)

    def get_database(self):
        from pymongo import MongoClient
        db_key = os.environ.get('DB_KEY')
        if db_key is None:
            logger.critical("NO DB KEY FOUND, USING LOCAL DB INSTEAD")
        client = MongoClient(db_key)
        db = client.KurzBot
        logger.info('Connected to mongoDB')
        return db

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
