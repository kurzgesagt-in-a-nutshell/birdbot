import os
import time
import json
import requests
import traceback

import psutil as ps
import discord
from discord.ext import commands

print("Hello!\nDelaying bot for (kinda) successful server creation.")
time.sleep(5)


config = json.load(open('config.json'))
bot = commands.AutoShardedBot(
    command_prefix=get_prefix, owners=config["owners"],
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
            await channel.send(f'<:boolyes:700827341659701248> Successfully reloaded. Took '
                               f'{round(time.time()-float(par[1])-5, 4)} '
                               f'seconds (5 seconds buffer.)')
        os.remove('__tmp_restart__.tmp')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,
                                                        name="to Steve's voice" ))

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
