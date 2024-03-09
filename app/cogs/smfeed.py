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
        smq_channel = self.bot._get_channel(Reference.Channels.social_media_queue)
        smf_channel = self.bot._get_channel(Reference.Channels.social_media_feed)
        message = await smq_channel.fetch_message(payload.message_id)
        for reaction in message.reactions:
            if isinstance(reaction.emoji, str):
                continue
            if reaction.emoji.id == Reference.Emoji.kgsYes and reaction.count <= 2:
                await smf_channel.send(message.content)
                break


async def setup(bot: BirdBot):
    await bot.add_cog(Smfeed(bot))
