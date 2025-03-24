# Copyright (C) 2024, Kurzgesagt Community Devs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

"""Initializes the implementation of the BirdBot class. Along with the setup function."""

import argparse
import asyncio
import io
import logging
import os
import traceback
from collections.abc import Generator
from contextlib import contextmanager, suppress
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Self

import certifi
import discord
import dotenv
from discord import Interaction, TextChannel, app_commands
from discord.abc import GuildChannel
from discord.ext import commands
from rich.logging import RichHandler

from .utils import errors
from .utils.config import Reference

_log = logging.getLogger(__name__)


@contextmanager
def logging_context() -> Generator[Any, Any, Any]:
    """Build the logger configuration."""
    logger = logging.getLogger()
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.INFO)
    try:
        dotenv.load_dotenv()

        logger.setLevel(int(os.environ.get("LOGGING_LEVEL") or 20))  # defaults to INFO
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
    """Subclass of app_commands.CommandTree to define the behavior for the birdbot tree.

    Handles thrown errors within the tree and interactions between all commands.
    """

    @classmethod
    async def maybe_responded(cls, interaction: Interaction, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Either responds or sends a followup on an interaction response."""
        if interaction.response.is_done():
            await interaction.followup.send(*args, **kwargs)

            return

        await interaction.response.send_message(*args, **kwargs)

    async def alert(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        """Attempt to alert the discord channel logs of an exception."""
        channel = await interaction.client.fetch_channel(Reference.Channels.Logging.dev)
        if not isinstance(channel, TextChannel):
            raise Exception("channel provided is not a TextChannel")

        content = traceback.format_exc()

        file = discord.File(io.BytesIO(bytes(content, encoding="UTF-8")), filename=f"{type(error)}.py")

        embed = discord.Embed(
            title="Unhandled Exception Alert",
            description=(
                f"```\nContext: \nguild:{interaction.guild!r}\n{interaction.channel!r}\n" f"{interaction.user!r}\n```"
            ),
        )

        await channel.send(embed=embed, file=file)

    async def on_error(self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        """Handle errors thrown within the command tree.

        Inform the user of failure and logs code errors.
        """
        if isinstance(error, errors.InternalError):
            # Inform user of failure ephemerally

            embed = error.format_notif_embed(interaction)
            await BirdTree.maybe_responded(interaction, embed=embed, ephemeral=True)

            return

        if isinstance(error, app_commands.TransformerError):
            # Raised when a type annotation fails to convert to its target type.
            user_shown_error = errors.TransformerError(
                content=(
                    f"Failed to convert {error.value} to "
                    f"{error.transformer._error_display_name}. Make sure member/channel/role exists."
                )
            )

            embed = user_shown_error.format_notif_embed(interaction)
            await BirdTree.maybe_responded(interaction, embed=embed, ephemeral=True)

            return

        if isinstance(error, app_commands.CheckFailure):
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
    """Main Bot, inherited from AutoShardedBot."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        super().__init__(*args, **kwargs)
        self.get_database()
        self.args = None

    @classmethod
    def from_parseargs(cls, args: argparse.Namespace) -> Self:
        """Create and return an instance of a Bot from argparse Namespace instance."""
        _log.info(args)
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
    def get_database(cls) -> None:
        """Return MongoClient instance to self.db."""
        from pymongo import MongoClient

        db_key = os.environ.get("DB_KEY")
        if db_key is None:
            _log.critical("NO DB KEY FOUND, USING LOCAL DB INSTEAD")
        client = MongoClient(db_key, tlsCAFile=certifi.where())
        db = client.KurzBot
        _log.info("Connected to mongoDB")
        cls.db = db

    async def setup_hook(self) -> None:
        """Async setup for after the bot logs in."""
        if self.args:
            await self.load_extensions("app/cogs", self.args)

    async def load_extensions(self, folder: Path | str, args: argparse.Namespace) -> None:
        """Iterate over the extension folder and attempt to load all python files found."""
        if folder is None:
            return
        extdir = Path(folder)

        if not extdir.is_dir():
            return

        for item in extdir.iterdir():
            # Ignore some cogs for the test bots.
            if item.stem in ("antiraid", "automod", "giveaway") and (args.beta or args.alpha):
                _log.debug("Skipping: %s", item.name)
                continue

            if item.name.startswith("_"):
                continue
            if item.is_dir():
                await self.load_extensions(item, args)
                continue

            if item.suffix == ".py":
                await self.try_load(item)

    async def try_load(self, path: Path) -> bool:
        """Attempt to load the given path and returns a boolean indicating successful status."""
        extension = ".".join(path.with_suffix("").parts)

        try:
            await self.load_extension(extension)
            return True
        except Exception:
            _log.exception("an error occurred while loading extension")
            return False

    async def close(self) -> None:
        """Close the Discord connection and the aiohttp sessions if any (future perhaps?)."""
        for ext in list(self.extensions):
            with suppress(Exception):
                await self.unload_extension(ext)

        for cog in list(self.cogs):
            with suppress(Exception):
                await self.remove_cog(cog)

        await super().close()

    async def on_ready(self) -> None:
        """Log when the bot is ready."""
        if self.user is None:
            raise Exception("self.user is None")
        _log.info("Logged in as")
        _log.info(f"\tUser: {self.user.name}")
        _log.info(f"\tID  : {self.user.id}")
        _log.info("------")

    """"
    From here on it's custom functions we can use in cogs.
    """

    def _user(self) -> discord.ClientUser:
        """Get self.bot.user.

        This can only be used after login, as user can't be none.
        """
        user = self.user
        if user is None:
            raise errors.InvalidFunctionUsage
        return user

    def ismainbot(self) -> bool:
        """Return if self.bot is mainbot.

        Only works after login.
        """
        return self._user().id == Reference.mainbot

    def _get_channel(self, id: int) -> discord.TextChannel:
        """Get a TextChannel based on a snowflake."""
        channel = self.get_channel(id)
        if not isinstance(channel, discord.TextChannel):
            raise errors.InvalidFunctionUsage
        return channel

    def get_mainguild(self) -> discord.Guild:
        """Return the guild object for the referenced guild."""
        guild = self.get_guild(Reference.guild)
        if guild is None:
            raise errors.InvalidFunctionUsage
        return guild
