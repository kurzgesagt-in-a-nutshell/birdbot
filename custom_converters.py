
from discord.ext.commands.converter import Converter, IDConverter, _get_from_guilds, _utils_get
from discord.ext.commands.errors import BadArgument

import re
import logging

def _get_id_match(argument):
    _id_regex = re.compile(r'([0-9]{15,21})$')
    return _id_regex.match(argument)


def memberconverter(ctx, argument):
    try:
        bot = ctx.bot
        guild = ctx.guild
        match = _get_id_match(argument) or re.match(r'<@!?([0-9]+)>$', argument)
        member = None
        if match is None:
            result = None
        else:
            user_id = int(match.group(1))
            if guild:
                result = guild.get_member(user_id) or _utils_get(ctx.message.mentions, id=user_id)
            else:
                result = _get_from_guilds(bot, 'get_member', user_id)

        return result
    except Exception as e:
        logging.error(str(e))
        return None


def get_members(ctx, *args):
    try:
        members = []
        extra = []
        got_members = False
        for a in args:
            result = memberconverter(ctx, a)
            if got_members == False:
                if result:
                    members.append(result)
                else:
                    got_members = True
                    extra.append(a)
            else:
                extra.append(a)
        
        if members == []:
            members = None
        if extra == []:
            extra = None

        return members, extra

    except Exception as e:
        logging.error(e)
        return None, None