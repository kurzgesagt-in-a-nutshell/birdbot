import logging

import discord
from discord.ext import commands

from app.birdbot import BirdBot
from app.utils.config import Reference


class Smfeed(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.logger = logging.getLogger("Smfeed")
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Smfeed")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """React to the twitter webhooks"""

        if not self.bot.ismainbot():
            return
        if message.channel.id == Reference.Channels.social_media_queue:
            await message.add_reaction(Reference.Emoji.PartialString.kgsYes)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """If mod or above reacts to twitter webhook tweet, sends it to proper channel"""
        if payload.member == None:
            return

        if (
            payload.channel_id != Reference.Channels.social_media_queue
            or payload.member.bot
            or payload.emoji.id != Reference.Emoji.kgsYes
        ):
            return

        guild = self.bot.get_mainguild()
        trainee_mod_role = guild.get_role(Reference.Roles.trainee_mod)
        if payload.member.top_role < trainee_mod_role:
            return
        channel = self.bot._get_channel(Reference.Channels.social_media_queue)
        message = await channel.fetch_message(payload.message_id)
        for reaction in message.reactions:
            if isinstance(reaction.emoji, str):
                continue
            if reaction.emoji.id == Reference.Emoji.kgsYes and reaction.count <= 2:
                await channel.send(message.content)
                break


async def setup(bot: BirdBot):
    await bot.add_cog(Smfeed(bot))
