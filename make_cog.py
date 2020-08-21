name = input('Cog Name: ')
text = f"""import logging

import discord
from discord.ext import commands


class {''.join(name.title().split())}(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('{''.join(name.title().split())}')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded {''.join(name.title().split())}')
    
    @commands.command()
    async def your_command(self, ctx):
        \"\"\"Command description\"\"\"
        await ctx.send('thing')
    

def setup(bot):
    bot.add_cog({''.join(name.title().split())}(bot))

"""
f = open(f"cogs/{'_'.join(name.casefold().split())}.py", 'w+')
f.write(text)
f.close()
print(f"Created cog with name {'_'.join(name.casefold().split())}.py in cogs directory")
