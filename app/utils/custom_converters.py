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
import re

from discord.ext import commands
from discord.ext.commands.converter import _get_from_guilds, _utils_get

logger = logging.getLogger("CustomConverters")


def _get_id_match(argument):
    _id_regex = re.compile(r"([0-9]{15,21})$")
    return _id_regex.match(argument)


def member_converter(ctx: commands.Context, argument):
    try:
        bot = ctx.bot
        guild = ctx.guild
        match = _get_id_match(argument) or re.match(r"<@!?([0-9]+)>$", argument)
        if match is None:
            result = None
        else:
            user_id = int(match.group(1))
            if guild:
                result = guild.get_member(user_id) or _utils_get(ctx.message.mentions, id=user_id)
            else:
                result = _get_from_guilds(bot, "get_member", user_id)

        return result
    except Exception as e:
        logging.error(str(e))
        return None


def get_members(ctx: commands.Context, *args):
    try:
        members = []
        extra = []
        got_members = False
        for a in args:
            result = member_converter(ctx, a)
            if not got_members:
                if result:
                    members.append(result)
                else:
                    got_members = True
                    extra.append(a)
            else:
                extra.append(a)

        if not members:
            members = None
        if not extra:
            extra = None

        return members, extra

    except Exception as e:
        logging.error(e)
        return None, None
