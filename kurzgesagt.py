import logging
import time

import discord
from discord.ext import commands
from rich.logging import RichHandler

import helper
from loglevels import setup as llsetup

llsetup()

logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
    handlers=[RichHandler()]
)

logger = logging.getLogger(__name__)
print("Delaying bot for server creation")
time.sleep(5)


class Bot(commands.AutoShardedBot):
    """Main Bot"""

    def __init__(self):
        # For Bird Bot
        # super().__init__(command_prefix=["!", "k!"], case_insensitive=True,
        #                  owner_ids={389718094270038018, 183092910495891467, 424843380342784011}, reconnect=True)

        # For Kurz Temp Bot
        # intents = discord.Intents.all()
        
        # intents = discord.Intents.all()
        super().__init__(command_prefix="kt!", case_insensitive=True,
                         owner_ids={389718094270038018, 183092910495891467, 424843380342784011}, reconnect=True)

        self.starttime = time.time()
        cogs = ['cogs.moderation', 'cogs.dev', 'cogs.help']
        fails = {}
        for i in cogs:
            try:
                super().load_extension(i)
                logger.info(f'Loading {i}')
            except Exception as e:
                logger.exception('Exception at {i}')
                fails[i] = e

    async def on_ready(self):
        logger.info('Logged in as')
        logger.info(f"\tUser: {self.user.name}")
        logger.info(f"\tID  : {self.user.id}")
        logger.info('------')
        # bot status
        activity = discord.Activity(type=discord.ActivityType.listening, name="Steve's Voice")
        await self.change_presence(activity=activity)

        # TIMED
        await helper.start_timed_actions(self)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        if isinstance(error, commands.MissingPermissions):
            pass

        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send("Missing Arguments. Please check syntax using help command.")

        elif isinstance(error, commands.CommandNotFound):
            pass

        else:
            logger.error(str(error))
            return await ctx.send("Can't execute the command!!")


with open('token_temp.txt') as tokenfile:
    token = tokenfile.read()

Bot().run(token)
