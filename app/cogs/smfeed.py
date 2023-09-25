<<<<<<< HEAD
=======
import json
>>>>>>> origin/public-refactor
import logging

import discord
from discord.ext import commands

from app.utils.config import Reference


class Smfeed(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Smfeed")
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Smfeed")

    @commands.Cog.listener()
    async def on_message(self, message):
        """React to the twitter webhooks"""

        if self.bot.user.id != Reference.mainbot:
            return
        if message.channel.id == Reference.Channels.social_media_queue:
            await message.add_reaction(Reference.Emoji.PartialString.kgsYes)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """If mod or above reacts to twitter webhook tweet, sends it to proper channel"""

        if self.bot.user.id != Reference.mainbot:
            return
        if (
            payload.channel_id == Reference.Channels.social_media_queue
            and not payload.member.bot
            and payload.emoji.id == Reference.Emoji.kgsYes
        ):
            guild = discord.utils.get(self.bot.guilds, id=Reference.guild)
            trainee_mod_role = guild.get_role(Reference.Roles.moderator_and_above())
            if payload.member.top_role >= trainee_mod_role:
                channel = guild.get_channel(Reference.Channels.social_media_queue)  # twitter posts
                message = await channel.fetch_message(payload.message_id)
                for reaction in message.reactions:
                    if type(reaction.emoji) != type(""):
                        if reaction.emoji.id == Reference.Emoji.kgsYes:
                            if reaction.count < 3:
                                channel = guild.get_channel(Reference.Channels.social_media_feed)  # social-media-feed
                                await channel.send(message.content)
                                break


async def setup(bot):
    await bot.add_cog(Smfeed(bot))
