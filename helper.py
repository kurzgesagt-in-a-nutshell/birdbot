import discord

import datetime
import logging
import asyncio
import os
import json

from database import infraction_db, timed_actions_db

def create_embed(author, users, action, reason, extra="None", color=discord.Color.blurple):
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
            user_str = user_str + f'{ u }  ({ u.id })' + "\n"

    embed = discord.Embed(title=f'{author.name}#{author.discriminator}', description=f'{author.id}', color=color)
    embed.add_field(name='User(s) Affected ', value=f'```{ user_str }```', inline=False)
    embed.add_field(name='Action',value=f'```{ action }```', inline=False)
    embed.add_field(name='Reason', value=f'```{ reason }```', inline=False)
    embed.add_field(name='Additional Info', value=f'```{ extra }```', inline=False)
    embed.set_footer(text=datetime.datetime.utcnow())

    return embed

def create_user_infraction(user):
    u = {

        "user_id": user.id,
        "user_name": user.name,
        "last_updated": datetime.datetime.utcnow(),
        "total_infractions":
            {
                "ban": 0,
                "kick": 0,
                "mute": 0,
                "warn": 0,
                "total": 0
            }
        ,
        "mute": [],
        "warn": [],
        "kick": [],
        "ban": []                    
    }
    infraction_db.insert_one(u)


def create_infraction(author, users, action, reason, time=None):

    infractions = []
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


def get_infractions(member):
    
    if member is None:

        infractions = infraction_db.find().limit(5)


        embed = discord.Embed(title='Infractions', description=f'Last 5 Infracetd User', color=discord.Color.green())
        for i in infractions:
            embed.add_field(name='{} ({})'.format(i['user_name'], i['user_id']), value='Total Infractions: {}'.format(i['total_infractions']['total']), inline=False)
        
        return embed

    else:

        embed = discord.Embed(title='Infractions', description=f'Member: { member.name }', color=discord.Color.green())
        i = infraction_db.find_one({"user_id": member.id})

        if i:

            embed.add_field(name='{} ({})'.format(i['user_name'], i['user_id']), value='```Total Infractions: {}```'.format(i['total_infractions']['total']), inline=False)
            
            warn_str = ""
            for w in i["warn"]:
                warn_str = warn_str + 'Author: {} ({})'.format(w['author_name'], w['author_id']) + "\n" \
                                    + 'Reason: {}'.format(w['reason']) + "\n" \
                                    + 'Date: {}'.format(w['datetime'].replace(microsecond=0)) + "\n\n"

            mute_str = ""
            for w in i["mute"]:
                mute_str = mute_str + 'Author: {} ({})'.format(w['author_name'], w['author_id']) + "\n" \
                                    + 'Reason: {}'.format(w['reason']) + "\n" \
                                    + 'Duration: {}'.format(w['duration']) + "\n" \
                                    + 'Date: {}'.format(w['datetime'].replace(microsecond=0)) + "\n\n"

            ban_str = ""
            for w in i["ban"]:
                ban_str = ban_str   + 'Author: {} ({})'.format(w['author_name'], w['author_id']) + "\n" \
                                    + 'Reason: {}'.format(w['reason']) + "\n" \
                                    + 'Duration: {}'.format(w['duration']) + "\n" \
                                    + 'Date: {}'.format(w['datetime'].replace(microsecond=0)) + "\n\n"

            kick_str = ""
            for w in i["warn"]:
                kick_str = kick_str + 'Author: {} ({})'.format(w['author_name'], w['author_id']) + "\n" \
                                    + 'Reason: {}'.format(w['reason']) + "\n" \
                                    + 'Date: {}'.format(w['datetime'].replace(microsecond=0)) + "\n\n"


            embed.add_field(name='Warns', value=f'```{ warn_str }```', inline=False)
            embed.add_field(name='Mutes', value=f'```{ mute_str }```', inline=False)
            embed.add_field(name='Bans', value= f'```{ ban_str }```', inline=False)
            embed.add_field(name='Kicks', value=f'```{ kick_str }```', inline=False)

        else:
            embed.add_field(name="No infraction found.", value="```User is clean.```")

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


def delete_time_action(ids):
    try:
        timed_actions_db.remove({"_id": {"$in": ids}})
    except Exception as e:
        logging.error(str(e))


def delete_time_actions_uid(u_id, action):
    '''
        Delete timed action by user_id
    '''
    try:
        timed_actions_db.remove({"user_id": u_id, "action": action})
    except Exception as e:
        logging.error(str(e))


async def start_timed_actions(bot):
    try:

        config_file = open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r')
        config_json = json.loads(config_file.read())

        guild = discord.utils.get(bot.guilds, id=414027124836532234)

        logging_channel = discord.utils.get(guild.channels, id=config_json['logging']['logging-channel'])
        mute_role = discord.utils.get(guild.roles, id=config_json['roles']['mute-role'])

        all_actions = timed_actions_db.find().sort("action_end", 1)


        for a in all_actions:

            if a['action_end'] > datetime.datetime.utcnow():
                rem_time = int((a['action_end'] - datetime.datetime.utcnow()).total_seconds())
                await asyncio.sleep(rem_time)

            if a['action'] == 'mute':
                user = discord.utils.get(guild.members, id=a['user_id'])
                await user.remove_roles(mute_role, reason="Time Expired")

                timed_actions_db.remove({"_id": a["_id"]})

            elif a['action'] == 'ban':  
                ban_list = await guild.bans()
                for b in ban_list:
                    if b.user.id in a['user_id']:
                        await guild.unban(b.user, reason="Time Expired")
            
                timed_actions_db.remove({"_id": a["_id"]})
            
            embed = discord.Embed(title='Timed Action', description='Time Expired', color=discord.Color.dark_blue())
            embed.add_field(name='User Affected', value='```{} ({})```'.format(a['user_name'], a['user_id']), inline=False)
            embed.add_field(name='Action', value='```Un-{}```'.format(a['action']), inline=False)
            await logging_channel.send(embed=embed)
    
    except Exception as e: 
        logging.error(str(e))
        