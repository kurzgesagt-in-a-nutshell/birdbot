import io
import asyncio
import json

import logging

from traceback import TracebackException

import discord
from discord.ext import commands
from discord.ext.commands import errors

from utils.helper import NoAuthorityError, DevBotOnly


class Errors(commands.Cog):
    """Catches all exceptions coming in through commands"""
    def __init__(self, bot):
        with open('config.json', 'r') as config_file:
            self.config_json = json.loads(config_file.read())
        self.dev_logging_channel = self.config_json['logging'][
            'dev_logging_channel']

        self.logger = logging.getLogger('Listeners')
        self.bot = bot

    async def react_send_delete(self,
                                ctx,
                                reaction=None,
                                message=None,
                                delay=6):
        """React to the command, send a message and delete later"""
        if reaction is not None:
            await ctx.message.add_reaction(reaction)
        if message is not None:
            await ctx.send(message, delete_after=delay)
        await asyncio.sleep(delay)
        await ctx.message.delete()

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Error listener')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, err):

        traceback_txt = ''.join(
            TracebackException.from_exception(err).format())
        channel = await self.bot.fetch_channel(self.dev_logging_channel)

        if isinstance(
                err,
            (errors.MissingPermissions, NoAuthorityError, errors.NotOwner)):
            await self.react_send_delete(
                ctx, reaction='<:kgsNo:610542174127259688>')

        elif isinstance(err, DevBotOnly):
            await self.react_send_delete(
                ctx,
                message='This command can only be run on the main bot',
                reaction='<:kgsNo:610542174127259688>')

        elif isinstance(err, commands.MissingRequiredArgument):
            await self.react_send_delete(
                ctx,
                message=
                f"You're missing the {err.param.name} argument. Please check syntax using the help command.",
                reaction='<:kgsNo:610542174127259688>')

        elif isinstance(err, commands.CommandNotFound):
            pass

        elif isinstance(err, errors.CommandOnCooldown):
            await self.react_send_delete(ctx, reaction='\U000023f0', delay=4)

        elif isinstance(err, errors.BadArgument):
            await self.react_send_delete(ctx,
                                         message=f"```{err}```",
                                         reaction='\U000023f0',
                                         delay=4)

        else:
            self.logger.exception(traceback_txt)
            await ctx.message.add_reaction('<:kgsStop:579824947959169024>')
            await ctx.send(
                "Uh oh, an unhandled exception occured, if this issue persists please contact FC or sloth"
            )
            description = f"An [**unhandled exception**]({ctx.message.jump_url}) occured in <#{ctx.message.channel.id}> when " \
                f"running the **{ctx.command.name}** command.```\n{err}```"
            embed = discord.Embed(title="Unhandled Exception",
                                  description=description,
                                  color=0xff0000)
            file = discord.File(io.BytesIO(traceback_txt.encode()),
                                filename='traceback.txt')
            await channel.send(embed=embed, file=file)


def setup(bot):
    bot.add_cog(Errors(bot))
