import argparse
import asyncio
import io
import logging
import os
import traceback
from contextlib import contextmanager, suppress
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import certifi
import discord
import dotenv
from discord import Interaction, TextChannel, app_commands
from discord.abc import GuildChannel
from discord.ext import commands
from rich.logging import RichHandler

from .utils import errors
from .utils.config import Reference

logger = logging.getLogger("BirdBot")


@contextmanager
def setup():
    logger = logging.getLogger()
    try:
        dotenv.load_dotenv()
        logging.getLogger("discord").setLevel(logging.INFO)
        logging.getLogger("discord.http").setLevel(logging.INFO)

        logger.setLevel(logging.DEBUG)
        dtfmt = "%Y-%m-%d %H:%M:%S"
        if not os.path.isdir("logs/"):
            os.mkdir("logs/")
        handlers = [
            RichHandler(rich_tracebacks=True),
            TimedRotatingFileHandler(filename="logs/birdbot.log", when="d", interval=5),
        ]
        fmt = logging.Formatter("[{asctime}] [{levelname:<7}] {name}: {message}", dtfmt, style="{")

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


class BirdTree(app_commands.CommandTree):
    """
    Subclass of app_commands.CommandTree to define the behavior for the birdbot
    tree.

    Handles thrown errors within the tree and interactions between all commands
    """

    @classmethod
    async def maybe_responded(cls, interaction: Interaction, *args, **kwargs):
        """
        Either responds or sends a followup on an interaction response
        """
        if interaction.response.is_done():
            await interaction.followup.send(*args, **kwargs)

            return

        await interaction.response.send_message(*args, **kwargs)

    async def alert(self, interaction: Interaction, error: app_commands.AppCommandError):
        """
        Attempts to altert the discord channel logs of an exception
        """

        channel = await interaction.client.fetch_channel(Reference.Channels.Logging.dev)
        assert isinstance(channel, TextChannel)

        content = traceback.format_exc()

        file = discord.File(io.BytesIO(bytes(content, encoding="UTF-8")), filename=f"{type(error)}.py")

        embed = discord.Embed(
            title="Unhandled Exception Alert",
            description=f"```\nContext: \nguild:{repr(interaction.guild)}\n{repr(interaction.channel)}\n{repr(interaction.user)}\n```",  # f"```py\n{content[2000:].strip()}\n```"
        )

        await channel.send(embed=embed, file=file)

    async def on_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        """Handles errors thrown within the command tree"""
        if isinstance(error, errors.InternalError):
            # Inform user of failure ephemerally

            embed = error.format_notif_embed(interaction)
            await BirdTree.maybe_responded(interaction, embed=embed, ephemeral=True)

            return
        elif isinstance(error, app_commands.CheckFailure):

            user_shown_error = errors.CheckFailure(content=str(error))

            embed = user_shown_error.format_notif_embed(interaction)
            await BirdTree.maybe_responded(interaction, embed=embed, ephemeral=True)

            return

        # most cases this will consist of errors thrown by the actual code

        if isinstance(interaction.channel, GuildChannel):
            is_in_public_channel = interaction.channel.category_id != Reference.Categories.moderation
        else:
            is_in_public_channel = False

        user_shown_error = errors.InternalError()
        await BirdTree.maybe_responded(
            interaction, embed=user_shown_error.format_notif_embed(interaction), ephemeral=is_in_public_channel
        )

        try:
            await self.alert(interaction, error)
        except app_commands.AppCommandError as e:
            await super().on_error(interaction, e)


class BirdBot(commands.AutoShardedBot):
    """Main Bot"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.get_database()
        self.args = None

    @classmethod
    def from_parseargs(cls, args: argparse.Namespace):
        """Create and return an instance of a Bot from argparse Namespace instance"""
        logger.info(args)
        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=True)
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
            activity = discord.Activity(type=discord.ActivityType.watching, name="for bugs")
        elif args.alpha:
            prefix = "a!"
            owner_ids = Reference.botdevlist
            activity = discord.Activity(type=discord.ActivityType.playing, name="imagine being a beta")
        else:
            prefix = "!"
            owner_ids = Reference.botownerlist
            max_messages = 10000
            activity = discord.Activity(type=discord.ActivityType.listening, name="Steve's voice")
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
        x.args = args
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

    async def setup_hook(self):
        """
        Async setup for after the bot logs in
        """
        if self.args:
            await self.load_extensions("app/cogs", self.args)

    async def load_extensions(self, folder: Path | str, args: argparse.Namespace) -> None:
        """
        Iterates over the extension folder and attempts to load all python files
        found.
        """

        if folder is None:
            return
        extdir = Path(folder)

        if not extdir.is_dir():
            return

        for item in extdir.iterdir():
            if item.stem in ("antiraid", "automod", "giveaway") and (args.beta or args.alpha):
                logger.debug("Skipping: %s", item.name)
                continue

            if item.name.startswith("_"):
                continue
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

        extension = ".".join(path.with_suffix("").parts)

        try:
            await self.load_extension(extension)
            return True
        except Exception as e:
            logger.error("an error occurred while loading extension", exc_info=e)
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
        assert self.user is not None
        logger.info("Logged in as")
        logger.info(f"\tUser: {self.user.name}")
        logger.info(f"\tID  : {self.user.id}")
        logger.info("------")

    """"
    custom functions we can use
    """
    def _user(self) -> discord.ClientUser:
        user = self.user
        if user == None:
            raise errors.InvalidFunctionUsage()
        return user

    def ismainbot(self) -> bool:
        if self._user().id == Reference.mainbot:
            return True
        return False

    def _get_channel(self, id: int) -> discord.TextChannel:
        channel = self.get_channel(id)
        if isinstance(channel, discord.abc.PrivateChannel | None | discord.Thread):
            raise errors.InvalidFunctionUsage()
        if isinstance(channel, discord.VoiceChannel | discord.CategoryChannel | discord.StageChannel | discord.ForumChannel):
            raise errors.InvalidFunctionUsage()
        return channel

    def get_mainguild(self) -> discord.Guild:
        guild = self.get_guild(Reference.guild)
        if guild == None:
            raise errors.InvalidFunctionUsage()
        return guild
