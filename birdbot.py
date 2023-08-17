import logging
import asyncio
import os
import discord
import dotenv
import certifi

from pathlib import Path
from contextlib import contextmanager, suppress
from logging.handlers import TimedRotatingFileHandler
from discord.ext import commands
from rich.logging import RichHandler

from utils.birdtree import BirdTree
from utils.config import Reference

logger = logging.getLogger("BirdBot")


@contextmanager
def setup():
    try:
        dotenv.load_dotenv()
        logging.getLogger("discord").setLevel(logging.INFO)
        logging.getLogger("discord.http").setLevel(logging.INFO)

        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        dtfmt = "%Y-%m-%d %H:%M:%S"
        if not os.path.isdir("logs/"):
            os.mkdir("logs/")
        handlers = [
            RichHandler(rich_tracebacks=True),
            TimedRotatingFileHandler(filename="logs/birdbot.log", when="d", interval=5),
        ]
        fmt = logging.Formatter(
            "[{asctime}] [{levelname:<7}] {name}: {message}", dtfmt, style="{"
        )

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

    currently_raided = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_database()

    @classmethod
    def from_parseargs(cls, args):
        """Create and return an instance of a Bot."""
        logger.info(args)
        allowed_mentions = discord.AllowedMentions(
            roles=False, everyone=False, users=True
        )
        loop = asyncio.get_event_loop()
        intents = discord.Intents(
            guilds=True,
            members=True,
            bans=True,
            emojis=True,
            webhooks=True,
            messages=True,
            reactions=True,
            message_content=True,
            presences=True,
        )
        max_messages = 1000
        if args.beta:
            prefix = "b!"
            owner_ids = Reference.botdevlist
            activity = discord.Activity(
                type=discord.ActivityType.watching, name="for bugs"
            )
        elif args.alpha:
            prefix = "a!"
            owner_ids = Reference.botdevlist
            activity = discord.Activity(
                type=discord.ActivityType.playing, name="imagine being a beta"
            )
        else:
            prefix = "!"
            owner_ids = Reference.botownerlist
            max_messages = 10000
            activity = discord.Activity(
                type=discord.ActivityType.listening, name="Steve's voice"
            )
        x = cls(
            loop=loop,
            max_messages=max_messages,
            command_prefix=commands.when_mentioned_or(prefix),
            owner_ids=owner_ids,
            activity=activity,
            case_insensitive=True,
            allowed_mentions=allowed_mentions,
            intents=intents,
            tree_cls=BirdTree,
        )

        x.get_database()
        return x

    @classmethod
    def get_database(cls):
        """Return MongoClient instance to self.db"""
        from pymongo import MongoClient

        db_key = os.environ.get("DB_KEY")
        if db_key is None:
            logger.critical("NO DB KEY FOUND, USING LOCAL DB INSTEAD")
        client = MongoClient(db_key, tlsCAFile=certifi.where())
        db = client.KurzBot
        logger.info("Connected to mongoDB")
        cls.db = db

    async def load_extensions(self, folder, args):
        """
        Iterates over the extension folder and attempts to load all python files
        found.
        """
        
        
        if folder is None: return
        extdir = Path(folder)

        if not extdir.is_dir(): return

        for item in extdir.iterdir():
            if (
                item.stem in ("antiraid", "automod", "giveaway")
                and (args.beta or args.alpha)
            ): 
                logger.debug("Skipping: %s", item.name)
                continue
            
            if item.name.startswith("_"): continue
            if item.is_dir():
                await self.load_extensions(item, args)
                continue

            if item.suffix == ".py":
                await self.try_load(item)

    async def try_load(self, path: Path) -> bool:
        """
        Attempts to load the given path and returns a boolean indicating
        successful status
        """
        
        extension = ".".join(path.with_suffix('').parts)

        try:
            await self.load_extension(extension)
            return True
        except Exception as e:
            logger.error(
                "an error occurred while loading extension", 
                exc_info=e
            )
            return False

    async def close(self):
        """Close the Discord connection and the aiohttp sessions if any (future perhaps?)."""
        for ext in list(self.extensions):
            with suppress(Exception):
                await self.unload_extension(ext)

        for cog in list(self.cogs):
            with suppress(Exception):
                await self.remove_cog(cog)

        await super().close()

    async def on_ready(self):
        logger.info("Logged in as")
        logger.info(f"\tUser: {self.user.name}")
        logger.info(f"\tID  : {self.user.id}")
        logger.info("------")
