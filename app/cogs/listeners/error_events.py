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
"""Holds evennt listeners related to command errors."""

import asyncio
import contextlib
import io
import logging
from traceback import TracebackException

import discord
from discord.ext import commands
from discord.ext.commands import errors

from app.birdbot import BirdBot
from app.utils.config import Reference
from app.utils.errors import CheckFailure, InternalError
from app.utils.helper import NoAuthorityError

_log = logging.getLogger(__name__)


class Errors(commands.Cog):
    """Catches all exceptions coming in through text commands."""

    def __init__(self, bot: BirdBot) -> None:
        self.dev_logging_channel = Reference.Channels.Logging.dev
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Log the module as ready."""
        _log.info("Loaded")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err: Exception) -> None:
        """Listen and report command errors."""
        if isinstance(err, commands.CommandNotFound):
            return

        traceback_txt = "".join(TracebackException.from_exception(err).format())
        channel = self.bot._get_channel(self.dev_logging_channel)

        if isinstance(err, InternalError):
            embed = err.format_notif_embed(ctx)

            await ctx.send(embed=embed, delete_after=5)
            await asyncio.sleep(5)
            with contextlib.suppress(discord.errors.NotFound):
                await ctx.message.delete()

        elif isinstance(
            err,
            (
                errors.MissingPermissions,
                NoAuthorityError,
                errors.NotOwner,
                errors.CheckAnyFailure,
                errors.CheckFailure,
            ),
        ):
            err = CheckFailure(content=str(err))

            embed = err.format_notif_embed(ctx)

            await ctx.send(embed=embed, delete_after=5)
            await asyncio.sleep(5)
            with contextlib.suppress(discord.errors.NotFound):
                await ctx.message.delete()

        else:
            _log.error(traceback_txt)
            await ctx.message.add_reaction(Reference.Emoji.PartialString.kgsStop)
            if not self.bot.ismainbot():
                return
            await ctx.send(
                "Uh oh, an unhandled exception occured, if this issue persists please contact any of bot devs (Sloth, FC, Austin, Orav, Source)."  # noqa: E501: line too long
            )
            description = (
                f"An [**unhandled exception**]({ctx.message.jump_url}) occured in <#{ctx.message.channel.id}> when "
                f"running the **{ctx.command.name}** command.```\n{err}```"  # type: ignore[reportOptionalMemberAccess]
            )
            embed = discord.Embed(title="Unhandled Exception", description=description, color=0xFF0000)
            file = discord.File(io.BytesIO(traceback_txt.encode()), filename="traceback.txt")
            await channel.send(embed=embed, file=file)


async def setup(bot: BirdBot) -> None:
    """Add the cog to the bot."""
    await bot.add_cog(Errors(bot))
