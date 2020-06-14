import time
import os
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='k!')

print("Hello!\nDelaying bot for (kinda) successful server creation.")
time.sleep(5)

@bot.event
async def on_ready():
    print('Logged in as')
    print(f"\tUser: {bot.user.name}")
    print(f"\tID  : {bot.user.id}")
    print('------')
    #bot status
    type = discord.ActivityType.listening
    activity = discord.Activity(type=type, name="to Steve's voice" )
    await bot.change_presence(activity = activity)

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
