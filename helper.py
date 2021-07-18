import asyncio
import datetime
import json
import logging

import discord
from discord.ext import commands

from database import infraction_db, timed_actions_db

config_json = json.load(open('config.json'))
config_roles = config_json["roles"]

# Custom checks

logger = logging.getLogger('Helper')


class NoAuthorityError(commands.CheckFailure):
    """Raised when user has no clearance to run a command"""
    pass


def helper_and_above():
    async def predicate(ctx):
        user_role_ids = [x.id for x in ctx.author.roles]
        check_role_ids = [config_roles["helper_role"], config_roles["mod_role"],
                          config_roles["mod_role"], config_roles["admin_role"], config_roles["kgsofficial_role"]]
        if not any(x in user_role_ids for x in check_role_ids):
            raise NoAuthorityError
        return True

    return commands.check(predicate)


def mod_and_above():
    async def predicate(ctx):
        user_role_ids = [x.id for x in ctx.author.roles]
        check_role_ids = [config_roles["mod_role"],
                          config_roles["admin_role"], config_roles["kgsofficial_role"]]
        if not any(x in user_role_ids for x in check_role_ids):
            raise NoAuthorityError
        return True

    return commands.check(predicate)


def admin_and_above():
    async def predicate(ctx):
        user_role_ids = [x.id for x in ctx.author.roles]
        check_role_ids = [config_roles["admin_role"],
                          config_roles["kgsofficial_role"]]
        if not any(x in user_role_ids for x in check_role_ids):
            raise NoAuthorityError
        return True
    return commands.check(predicate)


def create_embed(author, users, action, reason=None, extra=None, color=discord.Color.blurple, link=None):
    """
        Author: Message sender. (eg: ctx.author)
        Users: List of users affected (Pass None if no users)
        Action: Action/Command
        Reason: Reason
        Extra: Additional Info
        Color: Color of the embed
    """

    user_str = "None"
    if users is not None:
        user_str = ""

        for u in users:
            user_str = user_str + f'{u.mention}  ({u.id})' + "\n"

    embed = discord.Embed(title=f'{action}', description=f'Action By: {author.mention}', color=color,
                          timestamp=datetime.datetime.utcnow())
    embed.add_field(name='User(s) Affected ',
                    value=f'{user_str}', inline=False)

    if reason:
        embed.add_field(name='Reason', value=f'{reason}', inline=False)

    if extra:
        embed.add_field(name='Additional Info', value=f'{extra}', inline=False)

    if link:
        embed.add_field(name="Link", value=link, inline=False)

    # embed.set_footer(text=datetime.datetime.utcnow())

    return embed


def create_user_infraction(user):
    u = {

        "user_id": user.id,
        "user_name": user.name,
        "last_updated": datetime.datetime.utcnow(),
        "total_infractions": {
            "ban": 0,
            "kick": 0,
            "mute": 0,
            "warn": 0,
            "total": 0
        },
        "mute": [],
        "warn": [],
        "kick": [],
        "ban": []
    }
    infraction_db.insert_one(u)


def create_infraction(author, users, action, reason, time=None):
    for u in users:

        inf = infraction_db.find_one({"user_id": u.id})

        if inf is None:
            create_user_infraction(u)
            inf = infraction_db.find_one({"user_id": u.id})

        if action == 'mute':
            inf['mute'].append({
                "author_id": author.id,
                "author_name": author.name,
                "datetime": datetime.datetime.utcnow(),
                "reason": reason,
                "duration": time
            })
            inf['total_infractions']['mute'] = inf['total_infractions']['mute'] + 1
            inf['total_infractions']['total'] = inf['total_infractions']['total'] + 1

        elif action == 'ban':
            inf['ban'].append({
                "author_id": author.id,
                "author_name": author.name,
                "datetime": datetime.datetime.utcnow(),
                "reason": reason,
                "duration": time
            })
            inf['total_infractions']['ban'] = inf['total_infractions']['ban'] + 1
            inf['total_infractions']['total'] = inf['total_infractions']['total'] + 1

        elif action == 'kick':
            inf['kick'].append({
                "author_id": author.id,
                "author_name": author.name,
                "datetime": datetime.datetime.utcnow(),
                "reason": reason
            })
            inf['total_infractions']['kick'] = inf['total_infractions']['kick'] + 1
            inf['total_infractions']['total'] = inf['total_infractions']['total'] + 1

        elif action == 'warn':
            inf['warn'].append({
                "author_id": author.id,
                "author_name": author.name,
                "datetime": datetime.datetime.utcnow(),
                "reason": reason
            })
            inf['total_infractions']['warn'] = inf['total_infractions']['warn'] + 1
            inf['total_infractions']['total'] = inf['total_infractions']['total'] + 1

        inf['last_updated'] = datetime.datetime.utcnow()

        infraction_db.update_one({"user_id": u.id}, {"$set": inf})


def get_infractions(member_id, inf_type):

    infr = infraction_db.find_one({"user_id": member_id})

    embed = discord.Embed(title='Infractions', description=' ', color=discord.Color.green(),
                          timestamp=datetime.datetime.utcnow())

    if infr:

        embed.add_field(name='{} ({})'.format(infr['user_name'], infr['user_id']),
                        value='```Total Infractions: {}```'.format(infr['total_infractions']['total']), inline=False)

        if inf_type == 'warn':
            warn_str = ""
            for idx, warn in enumerate(infr["warn"]):
                warn_str = "{0}{1}\n{2}\n{3}\n\n".format(warn_str,
                                                         'Author: {} ({})'.format(
                                                             warn['author_name'], warn['author_id']),
                                                         'Reason: {}'.format(
                                                             warn['reason']),
                                                         'Date: {}'.format(warn['datetime'].replace(microsecond=0)))

                if (idx + 1) % 5 == 0:
                    embed.add_field(
                        name=f'Warns', value=f'```{warn_str}```', inline=False)
                    warn_str = ""

            if warn_str == "":
                warn_str = None

            embed.add_field(
                name=f'Warns', value=f'```{warn_str}```', inline=False)

        elif inf_type == 'mute':
            mute_str = ""
            for idx, mute in enumerate(infr["mute"]):
                mute_str = "{0}{1}\n{2}\n{3}\n{4}\n\n".format(mute_str,
                                                              'Author: {} ({})'.format(
                                                                  mute['author_name'], mute['author_id']),
                                                              'Reason: {}'.format(
                                                                  mute['reason']),
                                                              'Duration: {}'.format(
                                                                  mute['duration']),
                                                              'Date: {}'.format(mute['datetime'].replace(microsecond=0)))

                if (idx + 1) % 5 == 0:
                    embed.add_field(
                        name='Mutes', value=f'```{mute_str}```', inline=False)
                    mute_str = ""

            if mute_str == "":
                mute_str = None

            embed.add_field(
                name='Mutes', value=f'```{mute_str}```', inline=False)

        elif inf_type == 'ban':
            ban_str = ""
            for idx, ban in enumerate(infr["ban"]):
                ban_str = "{0}{1}\n{2}\n{3}\n{4}\n\n".format(ban_str,
                                                             'Author: {} ({})'.format(
                                                                 ban['author_name'], ban['author_id']),
                                                             'Reason: {}'.format(
                                                                 ban['reason']),
                                                             'Duration: {}'.format(
                                                                 ban['duration']),
                                                             'Date: {}'.format(ban['datetime'].replace(microsecond=0)))

                if (idx + 1) % 5 == 0:
                    embed.add_field(
                        name='Bans', value=f'```{ban_str}```', inline=False)
                    ban_str = ""

            if ban_str == "":
                ban_str = None

            embed.add_field(
                name='Bans', value=f'```{ban_str}```', inline=False)

        elif inf_type == 'kick':
            kick_str = ""
            for idx, kick in enumerate(infr["kick"]):
                kick_str = "{0}{1}\n{2}\n{3}\n\n".format(kick_str,
                                                         'Author: {} ({})'.format(
                                                             kick['author_name'], kick['author_id']),
                                                         'Reason: {}'.format(
                                                             kick['reason']),
                                                         'Date: {}'.format(kick['datetime'].replace(microsecond=0)))

                if (idx + 1) % 5 == 0:
                    embed.add_field(
                        name='Kicks', value=f'```{kick_str}```', inline=False)
                    kick_str = ""

            if kick_str == "":
                kick_str = None

            embed.add_field(
                name='Kicks', value=f'```{kick_str}```', inline=False)

    else:
        embed.add_field(name="No infraction found.",
                        value="```User is clean.```")

    return embed


def create_timed_action(users, action, time):
    try:
        data = []
        for u in users:
            data.append({
                "user_id": u.id,
                "user_name": u.name,
                "action": action,
                "action_start": datetime.datetime.utcnow(),
                "duration": time,
                "action_end": datetime.datetime.utcnow() + datetime.timedelta(seconds=time)
            })
        ids = timed_actions_db.insert_many(data)
        return ids.inserted_ids
    except Exception as e:
        logging.error(str(e))


def delete_timed_action(ids):
    try:
        timed_actions_db.remove({"_id": {"$in": ids}})
    except Exception as e:
        logging.error(str(e))


def delete_timed_actions_uid(u_id, action):
    """
        Delete timed action by user_id
    """
    try:
        timed_actions_db.remove({"user_id": u_id, "action": action})
    except Exception as e:
        logging.error(str(e))


async def start_timed_actions(bot):
    try:

        config_file = open('config.json', 'r')
        config_json = json.loads(config_file.read())

        guild = discord.utils.get(bot.guilds, id=414027124836532234)

        logging_channel = discord.utils.get(
            guild.channels, id=config_json['logging']['logging_channel'])
        mute_role = discord.utils.get(
            guild.roles, id=config_json['roles']['mute_role'])

        all_actions = timed_actions_db.find().sort("action_end", 1)

        for a in all_actions:

            if a['action_end'] > datetime.datetime.utcnow():
                rem_time = int(
                    (a['action_end'] - datetime.datetime.utcnow()).total_seconds())
                await asyncio.sleep(rem_time)

            if a['action'] == 'mute':
                user = discord.utils.get(guild.members, id=a['user_id'])
                await user.remove_roles(mute_role, reason="Time Expired")

                timed_actions_db.remove({"_id": a["_id"]})

            elif a['action'] == 'ban':
                ban_list = await guild.bans()
                for b in ban_list:
                    if b.user.id == a['user_id']:
                        await guild.unban(b.user, reason="Time Expired")
                    timed_actions_db.remove({"_id": a["_id"]})

            embed = discord.Embed(title='Timed Action', description='Time Expired', color=discord.Color.dark_blue(),
                                  timestamp=datetime.datetime.utcnow())
            embed.add_field(name='User Affected', value='```{} ({})```'.format(a['user_name'], a['user_id']),
                            inline=False)
            embed.add_field(
                name='Action', value='```Un-{}```'.format(a['action']), inline=False)
            await logging_channel.send(embed=embed)

    except Exception as e:
        logging.error(str(e))


def calc_time(args):
    tot_time = 0
    reason = None
    time_str = ""
    try:

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

                time_str = time_str + a + " "
                t = 0
                j = 0
                for i in a:

                    if i.isdigit():
                        t = t * pow(10, j) + int(i)
                        j = j + 1

                    else:
                        if i == 'w' or i == 'W':
                            tot_time = tot_time + t * 7 * 24 * 60 * 60
                        elif i == 'd' or i == 'D':
                            tot_time = tot_time + t * 24 * 60 * 60
                        elif i == 'h' or i == 'H':
                            tot_time = tot_time + t * 60 * 60
                        elif i == 'm' or i == 'M':
                            tot_time = tot_time + t * 60
                        elif i == 's' or i == 'S':
                            tot_time = tot_time + t

                        t = 0
                        j = 0

                r = r + 1

        if r < len(args):
            for a in args[r:]:
                if reason is None:
                    reason = a
                else:
                    reason = reason + " " + a

        else:
            return None, None, None

        if time_str == "":
            time_str = tot_time.__str__()

        return tot_time, reason, time_str.strip()

    except Exception as ex:
        logging.error(str(ex))
        return None, -1, None


def get_timed_actions():
    try:
        return timed_actions_db.find().sort("action_end", 1)

    except Exception as e:
        logging.exception(e)
