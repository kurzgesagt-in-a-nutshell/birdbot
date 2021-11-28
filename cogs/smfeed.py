import logging
import json

import discord
from discord.ext import commands


class Smfeed(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Smfeed")
        self.bot = bot

        with open("config.json", "r") as config_file:
            config_json = json.loads(config_file.read())

        self.trainee_mod_role = config_json["roles"]["trainee_mod_role"]

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Smfeed")

    @commands.Cog.listener()
    async def on_message(self, message):
        """React to the twitter webhooks"""
        if message.channel.id == 580354435302031360:
            await message.add_reaction("<:kgsThis:567150184853798912>")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """If mod or above reacts to twitter webhook tweet, sends it to proper channel"""
        if (
            payload.channel_id == 580354435302031360
            and not payload.member.bot
            and payload.emoji.id == 567150184853798912
        ):
            guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
            trainee_mod_role = guild.get_role(self.trainee_mod_role)
            if payload.member.top_role >= trainee_mod_role:
                channel = self.bot.get_channel(489450008643502080)  # social-media-feed
                message = await channel.fetch_message(payload.message_id)
                await channel.send(message.content)


def setup(bot):
    bot.add_cog(Smfeed(bot))
