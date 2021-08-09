import logging
import asyncio
import os
import discord
import dotenv
import time

from contextlib import contextmanager, suppress
from logging.handlers import TimedRotatingFileHandler
from discord.ext import commands
from rich.logging import RichHandler

logger = logging.getLogger('BirdBot')

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
            RichHandler(),
            TimedRotatingFileHandler(filename='logs/birdbot.log', when='d',interval=5)
        ]
        fmt = logging.Formatter(
            '[{asctime}] [{levelname:<7}] {name}: {message}', dtfmt, style='{')

        for handler in handlers:
            if isinstance(handler, TimedRotatingFileHandler):
                handler.setFormatter(fmt)
            logger.addHandler(handler)

        yield
    finally:
        handlers = logger.handlers[:]
        for handler in handlers:
            handler.close()
            logger.removeHandler(handler)


class BirdBot(commands.AutoShardedBot):
    """Main Bot"""
    db = None
    def __init__(self, *args, **kwargs):
        db = self.get_database()
        super().__init__(*args, **kwargs)

    @classmethod
    def from_parseargs(cls, args) -> "Bot":
        """Create and return an instance of a Bot."""
        logger.info(args)
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
        elif args.alpha:
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

    @classmethod
    def get_database(cls):
        """Return MongoClient instance to self.db"""
        from pymongo import MongoClient
        db_key = os.environ.get('DB_KEY')
        if db_key is None:
            logger.critical("NO DB KEY FOUND, USING LOCAL DB INSTEAD")
        client = MongoClient(db_key)
        db = client.KurzBot
        logger.info('Connected to mongoDB')
        cls.db = db

    def load_extensions(self):
        """Loads all cogs from cogs/ without the '_' prefix"""
        for filename in os.listdir('cogs/'):
            if not filename.startswith("_"):
                logger.info(f"loading {f'cogs.{filename[:-3]}'}")
                try:
                    self.load_extension(f"cogs.{filename[:-3]}")
                except Exception as e:
                    logger.error(
                        f"cogs.{filename[:-3]} cannot be loaded. [{e}]")
                    logger.exception(
                        f"Cannot load cog {f'cogs.{filename[:-3]}'}")

    async def close(self):
            """Close the Discord connection and the aiohttp sessions if any (future perhaps?)."""
            for ext in list(self.extensions):
                with suppress(Exception):
                    self.unload_extension(ext)

            for cog in list(self.cogs):
                with suppress(Exception):
                    self.remove_cog(cog)

            await super().close()


    async def on_ready(self):
        logger.info('Logged in as')
        logger.info(f"\tUser: {self.user.name}")
        logger.info(f"\tID  : {self.user.id}")
        logger.info('------')


