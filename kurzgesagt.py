import os
import time
import json
import requests
import traceback

import psutil as ps
import discord
from discord.ext import commands
<<<<<<< HEAD
prefix = 'k!'
bot = commands.Bot(command_prefix=prefix)
token = 'NDcxNzA1NzE4OTU3ODAxNDgz.XN7cLw.ntikeK86SgIq58QCw4_apMPfI30'
<<<<<<< HEAD
token2='NjM5NTA4NTE3NTM0OTU3NTk5.Xn4Wgg.BLKvrblu-10X-GSG7rQIyqoAM0I'
=======
token2='NjM5NTA4NTE3NTM0OTU3NTk5.Xb7V5Q.O3WHaQhujIDljrqEe2aiDbAex2I'
>>>>>>> f8205c6341d78643db977372189bd083316cbb41
=======
>>>>>>> sloth

print("Hello!\nDelaying bot for (kinda) successful server creation.")
time.sleep(5)


config = json.load(open('config.json'))
bot = commands.AutoShardedBot(
    command_prefix=get_prefix, owners=config["owners"],
    case_insensitive=True)
loaded = []
notloaded = {}


@bot.event
<<<<<<< HEAD
async def on_ready(): 
 print("working")
 ks = bot.get_guild(414027124836532234)
 jk=bot.get_guild(482936367043837972)

=======
async def on_ready():
<<<<<<< HEAD
 ks = bot.get_guild(414027124836532234)
 jk=bot.get_guild(482936367043837972)
 await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name="to Steve's voice"))
 
>>>>>>> f8205c6341d78643db977372189bd083316cbb41
 
 
 
  
     
 #announcement_channel=bot.get_channel(414064220196306968)
 #msg= await announcement_channel.fetch_message(623541883825553450)
 #await msg.edit(content='<:bird_thonk:606149684922155018>',embed=temp_announcement2)
 #rm=bot.get_channel(558333807548432395)
 #await rm.send(embed=welcome_menu)
 #rulech=bot.get_channel(414268041787080708)
 #msg=await rulech.fetch_message(564349454254211073)
 #await msg.edit(embed=embed)
=======
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
>>>>>>> sloth



bot.run(open('token.txt').read(), reconnect=True)
