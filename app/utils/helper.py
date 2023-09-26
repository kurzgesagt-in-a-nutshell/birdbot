import datetime
import logging
import re

from typing import List, Tuple

import discord
from discord.ext import commands

from app.birdbot import BirdBot

infraction_db = BirdBot.db.Infraction
timed_actions_db = BirdBot.db.TimedAction
cmd_blacklist_db = BirdBot.db.CommandBlacklist

from .config import Reference

logger = logging.getLogger("Helper")


# commands from third party bots
possible_prefixes = r"^([$+,\-.;>]|t!|p//)"
possible_commands = [
    # common for everyone (mostly)
    r"help",
    r"info",
    r"invite",
    r"ping",
    # Compiler#6201
    r"invite",
    r"compile(rs)?",
    r"languages",
    r"asm",
    r"botinfo",
    r"cpp",
    r"formats?",
    # SongBird
    r"play(next|erstats|lists)?",
    r"previous",
    r"scsearch",
    r"select",
    r"announce",
    r"bassboost",
    r"forceskip",
    r"pause",
    r"repeat",
    r"resume",
    r"seek",
    r"shuffle",
    r"skip",
    r"stop",
    r"volume",
    r"(clear|un)?queue",
    r"deduplicate",
    r"move",
    r"now",
    r"removeabsent",
    r"save(all)?",
    r"undo",
    r"about",
    r"details",
    r"lyrics",
    r"settings",
    r"stats",
    # TeXit#0796
    r"tex(config|doc)?",
    r"autotex",
    r"(guild)?preamble",
    r"ctan",
    r"calc",
    r"nlab",
    r"query",
    # YAGPDB.xyz#8760 (only include enabled commands)
    r"remindme",
    r"who(is|ami)",
    # Go4Liftoff Bot#1922
    r"ll",
    r"nl",
    r"listlaunches",
    r"nextlaunch",
    # Tatsu#8792 (add commands that frequently get used coz too many to add manually)
    r"rank",
    r"fish",
    r"rep",
    r"profile",
    r"cookie",
    r"quest",
    r"tg",
    r"tatsugotchi",
    r"pet",
    r"slots?",
    r"top",
    r"view ",
    r"viewnav",
    r"place",
    r"toggleskip",
    r"togglereminder ",
    r"palette",
    r"colours",
]


# ----Exception classes begin------#
class NoAuthorityError(commands.CheckFailure):
    """Raised when user has no clearance to run a command"""


class WrongChannel(commands.CheckFailure):
    """Raised when trying to run a command in the wrong channel"""

    def __init__(self, id):
        super().__init__(f"This command can only be run in <#{id}>")


class DevBotOnly(commands.CheckFailure):
    """Raised when trying to run commands meant for dev bots"""


# ----Exception classes end------#


def is_internal_command(bot: commands.AutoShardedBot, message: discord.Message):
    """
    check if message is a bird bot command
    returns bool
    """
    for x in bot.commands:
        if any(message.content.startswith(f"!{y}") for y in x.aliases):
            return True
        if message.content.startswith(f"!{x.name}"):
            return True
    return False


def is_external_command(message: discord.Message):
    """
    check if message is a third party bot command
    returns bool
    """
    for command in possible_commands:
        if re.match(possible_prefixes + command, message.content, re.IGNORECASE):
            return True
    return False


def create_embed(
    author: discord.User | discord.Member,
    action: str,
    users: List[discord.User | discord.Member] | None = None,
    reason=None,
    extra=None,
    color=discord.Color.blurple,
    link=None,
    inf_level=None,
) -> discord.Embed:
    """
    Creates an embed

    Args:
        author (discord.User or discord.Member): The author of the action (eg ctx.author)
        action (str): Action/Command Performed
        users (list(discord.User or discord.Member)): List of users affected. Defaults to None
        reason (str, optional): Reason. Defaults to None.
        extra (str, optional): Any additional info. Defaults to None.
        color (discord.Color, optional): Embed color. Defaults to discord.Color.blurple.
        link (str, optional): Link, if any. Defaults to None.

    Returns:
        discord.Embed: An embed with provided information.
    """
    user_str = "None"
    if users is not None:
        user_str = ""
        for u in users:
            user_str = f"{user_str} <@{u.id}>  ({u.id}) \n"

    embed = discord.Embed(
        title=f"{action}",
        description=f"Action By: {author.mention}",
        color=color,
        timestamp=datetime.datetime.utcnow(),
    )
    embed.add_field(name="User(s) Affected ", value=f"{user_str}", inline=False)

    if reason:
        embed.add_field(name="Reason", value=f"{reason}", inline=False)

    if extra:
        embed.add_field(name="Additional Info", value=f"{extra}", inline=False)

    if link:
        embed.add_field(name="Link", value=link, inline=False)

    if inf_level:
        embed.add_field(name="Level", value=inf_level, inline=False)

    return embed


def create_timed_action(users: List[discord.User | discord.Member], action: str, time: int):
    # TODO DELETE
    """Creates a database entry for timed action [not in use currently]

    Args:
        users (List[discord.User | discord.Member]): List of affected users
        action (str): Action ("mute")
        time (int): Duration for which action will last
    """
    data = []
    for u in users:
        data.append(
            {
                "user_id": u.id,
                "user_name": u.name,
                "action": action,
                "action_start": datetime.datetime.utcnow(),
                "duration": time,
                "action_end": datetime.datetime.utcnow() + datetime.timedelta(seconds=time),
            }
        )
    ids = timed_actions_db.insert_many(data)


def delete_timed_actions_uid(u_id: int):
    # TODO DELETE
    """delete timed action by user_id [not in use currently]

    Args:
        u_id (int): user's id
    """
    timed_actions_db.remove({"user_id": u_id})


def calc_time(args: List[str]) -> Tuple[int | None, str | None]:
    """Parses time from given list.
    Example:
    ["1hr", "12m30s", "extra", "string"] => (4350, "extra string")

    Args:
        args (List[str]): List of strings that needs to be parsed

    Returns:
        Tuple[int, str]: Returns parsed time (in seconds) and extra string.
    """
    tot_time = 0
    extra = None
    try:
        try:
            default_v = int(args[0])
            extra = " ".join(args[1:])

            if extra == "":
                return None, None

            return default_v * 60, " ".join(args[1:])
        except ValueError:
            pass

        r = 0
        for a in args:
            s = 0
            for c in a:
                if c.isdigit():
                    s = s + 1
                else:
                    break

            if a[:s] == "":
                break
            else:
                t = 0
                for i in a:
                    if i.isdigit():
                        t = t * 10 + int(i)

                    else:
                        if i == "w" or i == "W":
                            tot_time = tot_time + t * 7 * 24 * 60 * 60
                        elif i == "d" or i == "D":
                            tot_time = tot_time + t * 24 * 60 * 60
                        elif i == "h" or i == "H":
                            tot_time = tot_time + t * 60 * 60
                        elif i == "m" or i == "M":
                            tot_time = tot_time + t * 60
                        elif i == "s" or i == "S":
                            tot_time = tot_time + t

                        t = 0

                r = r + 1

        if r < len(args):
            for a in args[r:]:
                if extra is None:
                    extra = a
                else:
                    extra = extra + " " + a

        else:
            return None, None

        return tot_time, extra

    except Exception as ex:
        logging.error(str(ex))
        return None, None


def get_time_string(t: int) -> str:
    """Convert provided time input (seconds) to Day-Hours-Mins-Second string

    Args:
        t (int): Time in seconds

    Returns:
        str: Time string (Format: D-days H-hours M-mins S-seconds)
    """
    day = t // (24 * 3600)
    t = t % (24 * 3600)
    hour = t // 3600
    t %= 3600
    minutes = t // 60
    t %= 60
    seconds = t
    return f"{day}days {hour}hours {minutes}mins {seconds}sec"


def get_timed_actions():
    # TODO DELETE
    """Fetch all timed action from db [not in use currently]"""
    return timed_actions_db.find().sort("action_end", 1)


def create_automod_embed(
    message: discord.Message,
    automod_type: str,
):
    """Create embed for automod

    Args:
        message (discord.Message): The message object
        automod_type (str): Type of automod (eg.: "Profanity", "Spam", "Bypass" etc.)

    Returns:
        embed: A discord.Embed object.
    """
    assert isinstance(message.channel, discord.TextChannel)
    embed = discord.Embed(
        title=f"Message deleted. ({automod_type})",
        description=f"Message author: {message.author.mention}\nChannel: {message.channel.mention}",
        color=discord.Colour.dark_orange(),
        timestamp=datetime.datetime.utcnow(),
    )
    embed.add_field(
        name="Message Content",
        value=f"{message.content[:1024]}" if message.content else "it's an attachment/embed",
        inline=False,
    )
    return embed


def get_active_staff(bot: discord.Client) -> str:
    """
    Gets string containing mentions of active staff (mods, trainee mods and admins)
    Mentions both mod roles if no mod is online
    Returns: str
    """

    guild = discord.utils.get(bot.guilds, id=Reference.guild)
    assert guild
    active_staff = []
    mods_active = False
    for role_id in [Reference.Roles.moderator, Reference.Roles.administrator, Reference.Roles.trainee_mod]:
        role = discord.utils.get(guild.roles, id=role_id)
        assert role
        for member in role.members:
            if member.bot:
                continue
            if member in active_staff:
                continue
            if member.status == discord.Status.online or member.status == discord.Status.idle:
                active_staff.append(member)

                if not mods_active:
                    if member.top_role.id in [Reference.Roles.moderator, Reference.Roles.trainee_mod]:
                        # check for active mods
                        mods_active = True

    mention_str = " ".join([staff.mention for staff in active_staff])

    if not mods_active:
        mention_str += f"<@&{Reference.Roles.moderator}> <@&{Reference.Roles.trainee_mod}>"

    return mention_str


# This is useless due to slash migration
def blacklist_member(bot: commands.AutoShardedBot, member: discord.Member, command: commands.Command):
    """
    Blacklists a member from a command
    """

    cmd = cmd_blacklist_db.find_one({"command_name": command.name})
    if cmd is None:
        cmd_blacklist_db.insert_one({"command_name": command.name, "blacklisted_users": [member.id]})
        return

    cmd_blacklist_db.update_one({"command_name": command.name}, {"$push": {"blacklisted_users": member.id}})


# This is useless due to slash migration
def whitelist_member(member: discord.Member, command: commands.Command) -> bool:
    """
    Whitelist a member from a command and return True
    If user is not blacklisted return False
    """
    cmd = cmd_blacklist_db.find_one({"command_name": command.name})
    if cmd is None or member.id not in cmd["blacklisted_users"]:
        return False

    cmd_blacklist_db.update_one({"command_name": command.name}, {"$pull": {"blacklisted_users": member.id}})
    return True


def is_public_channel(channel: discord.TextChannel | discord.Thread) -> bool:
    """
    Returns true for all channels except those under the moderation category

    Currently used within the moderation cog to determine if an interaction
    should be ephemeral
    """

    return channel.category_id != Reference.Categories.moderation
