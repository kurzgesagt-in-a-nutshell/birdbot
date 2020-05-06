import os
import time
import json
import requests
import traceback

import asyncio

import psutil as ps
import discord
from discord.ext import commands

from enum import Enum
import logging

#logging.basicConfig(level=logging.INFO)

print("Hello!\nDelaying bot for (kinda) successful server creation.")
time.sleep(5)


config = json.load(open('config.json'))
bot = commands.AutoShardedBot(command_prefix='k!',
    owners=config["owners"],
    case_insensitive=True)
loaded = []
notloaded = {}


@bot.event
async def on_ready():
    print('Logged in as')
    print(f"\tUser: {bot.user.name}")
    print(f"\tID  : {bot.user.id}")
    print('------')
    if os.path.exists('__tmp_restart__.tmp'):
        with open('__tmp_restart__.tmp') as f:
            par = f.read().split(',')
            channel = await bot.fetch_channel(par[0])
            await channel.send(f'<Successfully reloaded. Took '
                               f'{round(time.time()-float(par[1])-5, 4)} '
                               f'seconds (5 seconds buffer.)')
        os.remove('__tmp_restart__.tmp')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="to Steve's voice" ))

    '''class FlagsEnum(Enum):
        EMPLOYEE = 1
        PARTNER = 2
        HYPESQUAD_EVENTS = 4
        BUG_HUNTER = 8
        HYPESQUAD_BRAVERY = 64
        HYPESQUAD_BRILLIANCE = 128
        HYPESQUAD_BALANCE = 256
        EARLY_SUPPORTER = 512
        BUG_HUNTER_TIER_TWO = 16384
        VERIFIED_BOT_DEVELOPER = 131072


    async def get_badges(user_id):
        await asyncio.sleep(3)
        user = await bot.http.request(discord.http.Route("GET", f"/users/{user_id}"))
        flags = user["public_flags"]

        badges = []
        for flag in FlagsEnum:
            if flags & flag.value:
                badges.append(flag.name)
        return badges
    for member in bot.get_guild(414027124836532234).members:
        badges = await get_badges(member.id)
        if "HYPESQUAD_EVENTS" in badges:
            await bot.get_channel(414179142020366336).send(f'{member.name} : HSE')
        if "PARTNER" in badges:
            await bot.get_channel(414179142020366336).send(f'{member.name} : Partner')
        if "EMPLOYEE" in badges:
            await bot.get_channel(414179142020366336).send(f'{member.name} : Employee')
        if "BUG_HUNTER" in badges:
            await bot.get_channel(414179142020366336).send(f'{member.name} : BH')'''

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        try:
            bot.load_extension(f'cogs.{filename[:-3]}')
        except Exception as error:
            print("{0} cannot be loaded. [{1}]".format(
                f'cogs.{filename[:-3]}', error))
            print(''.join(traceback.TracebackException.from_exception(error).format()))
        else:
            loaded.append(f'cogs.{filename[:-3]}')



bot.run(open('token.txt').read(), reconnect=True)
