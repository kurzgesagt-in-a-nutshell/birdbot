import io
import asyncio
import logging
from traceback import TracebackException

import discord
from discord.ext import commands
from discord.ext.commands import errors

from app.utils.errors import * 
from app.utils.helper import (
    NoAuthorityError,
)
from app.utils.config import Reference


class Errors(commands.Cog):
    """Catches all exceptions coming in through commands"""

    def __init__(self, bot):
        self.dev_logging_channel = Reference.Channels.Logging.dev

        self.logger = logging.getLogger("Listeners")
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Error listener")

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, err):
        
        if isinstance(err, commands.CommandNotFound):
            return

        traceback_txt = "".join(TracebackException.from_exception(err).format())
        channel = await self.bot.fetch_channel(self.dev_logging_channel)

        if isinstance(err, InternalError):
            embed = err.format_notif_embed(ctx)

            await ctx.send(embed=embed, delete_after=5)
            await asyncio.sleep(5)
            try:
                await ctx.message.delete()
            except discord.errors.NotFound:
                pass

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
            try:
                await ctx.message.delete()
            except discord.errors.NotFound:
                pass

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