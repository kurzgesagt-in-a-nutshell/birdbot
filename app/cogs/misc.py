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

"""Misc bot functionality."""
import logging
import re

import demoji
import discord
from discord import app_commands
from discord.ext import commands

from app.birdbot import BirdBot
from app.utils import checks
from app.utils.config import Reference

_log = logging.getLogger(__name__)


class Misc(commands.Cog):
    def __init__(self, bot: BirdBot) -> None:
        self.bot = bot

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.checks.cooldown(1, 10)
    @checks.bot_commands_only()
    async def big_emote(self, interaction: discord.Interaction, emoji: str) -> None:
        """Get image for server emote.

        Parameters
        ----------
        emoji: str
            Discord Emoji (only use in #bot-commands)

        """
        if len(demoji.findall_list(emoji)) == 1:
            code = (
                str(emoji.encode("unicode-escape"))
                .replace("U000", "-")
                .replace("\\", "")
                .replace("'", "")
                .replace("u", "-")[2:]
            )
            name = demoji.replace_with_desc(emoji).replace(" ", "-").replace(":", "").replace("_", "-")
            await interaction.response.send_message(
                "https://em-content.zobj.net/thumbs/160/twitter/322/" + name + "_" + code + ".png"
            )
        elif len(demoji.findall_list(emoji)) > 1:
            await interaction.response.send_message("please only send one emoji")
        else:
            if re.match(r"<a:\w+:(\d{17,19})>", str(emoji)):
                emoji = str(re.findall(r"<a:\w+:(\d{17,19})>", str(emoji))[0]) + ".gif"
                await interaction.response.send_message("https://cdn.discordapp.com/emojis/" + str(emoji))
            elif re.match(r"<:\w+:(\d{17,19})>", str(emoji)):
                emoji = str(re.findall(r"<:\w+:(\d{17,19})>", str(emoji))[0]) + ".png"
                await interaction.response.send_message("https://cdn.discordapp.com/emojis/" + str(emoji))
            else:
                await interaction.response.send_message("Could not process this emoji")


async def setup(bot: BirdBot) -> None:
    await bot.add_cog(Misc(bot))
