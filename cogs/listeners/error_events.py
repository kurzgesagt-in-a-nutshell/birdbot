import io
import asyncio
import requests
from requests.models import PreparedRequest
import json
import aiohttp
import logging
import random
import re

from traceback import TracebackException

import discord
from discord.ext import commands
from discord.ext.commands import errors
from discord import app_commands

from birdbot import BirdBot

from utils import app_checks
from utils.infraction import InfractionList
from utils.helper import (
    NoAuthorityError,
    DevBotOnly,
    WrongChannel,
    is_internal_command,
)
from utils.config import Reference


class Errors(commands.Cog):
    """Catches all exceptions coming in through commands"""

    def __init__(self, bot):
        self.dev_logging_channel = Reference.Channels.Logging.dev

        self.logger = logging.getLogger("Listeners")
        self.bot = bot

    async def react_send_delete(
        self,
        ctx: commands.Context,
        reaction: str = None,
        message: str = None,
        delay: int = 6,
    ):
        """React to the command, send a message and delete later"""
        if reaction is not None:
            await ctx.message.add_reaction(reaction)
        if message is not None:
            await ctx.send(message, delete_after=delay)
        await ctx.message.delete(delay=delay)

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Error listener")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err):

        traceback_txt = "".join(TracebackException.from_exception(err).format())
        channel = await self.bot.fetch_channel(self.dev_logging_channel)

        if isinstance(
            err,
            (
                errors.MissingPermissions,
                NoAuthorityError,
                errors.NotOwner,
                errors.CheckAnyFailure,
                errors.CheckFailure,
            ),
        ):
            await self.react_send_delete(ctx, reaction="<:kgsNo:955703108565098496>")

        elif isinstance(err, DevBotOnly):
            await self.react_send_delete(
                ctx,
                message="This command can only be run on the main bot",
                reaction="<:kgsNo:955703108565098496>",
            )

        elif isinstance(err, commands.MissingRequiredArgument):
            await self.react_send_delete(
                ctx,
                message=f"You're missing the {err.param.name} argument. Please check syntax using the help command.",
                reaction="<:kgsNo:955703108565098496>",
            )

        elif isinstance(err, commands.CommandNotFound):
            pass

        elif isinstance(err, errors.CommandOnCooldown):
            await self.react_send_delete(ctx, reaction="\U000023f0", delay=4)

        elif isinstance(err, (WrongChannel, errors.BadArgument)):
            await self.react_send_delete(
                ctx,
                message=err,
                reaction="<:kgsNo:955703108565098496>",
                delay=4,
            )

        else:
            self.logger.exception(traceback_txt)
            await ctx.message.add_reaction("<:kgsStop:579824947959169024>")
            if self.bot.user.id != Reference.mainbot:
                return
            await ctx.send(
                "Uh oh, an unhandled exception occured, if this issue persists please contact any of bot devs (Sloth, FC, Austin, Orav)."
            )
            description = (
                f"An [**unhandled exception**]({ctx.message.jump_url}) occured in <#{ctx.message.channel.id}> when "
                f"running the **{ctx.command.name}** command.```\n{err}```"
            )
            embed = discord.Embed(
                title="Unhandled Exception", description=description, color=0xFF0000
            )
            file = discord.File(
                io.BytesIO(traceback_txt.encode()), filename="traceback.txt"
            )
            await channel.send(embed=embed, file=file)


async def setup(bot):
    await bot.add_cog(Errors(bot))