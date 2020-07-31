import logging

import discord
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Help')
        self.bot = bot
        self.bot.remove_command('help')
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Help')
    
    @commands.command()
    async def help(self, ctx, cmnd=None):
        """help"""
        cogs = ['Moderation']
        try:
            if cmnd == None:
                embed=discord.Embed(title="Kurzbot help", description=f'To see more info do help [command].')
                for i in cogs:
                    cog = self.bot.get_cog(i)
                    commands = cog.get_commands()
                    commands = ['`' + c.name + '`' for c in commands]
                    embed.add_field(name=i, value='\n'.join(commands))
            elif self.bot.get_command(cmnd).cog_name in cogs:
                embed=discord.Embed(title="Kurzbot help", description=" ")
                command = self.bot.get_command(cmnd)
                embed.add_field(name=command.name, value=command.help)
        except:
            await ctx.send(f"Command `{cmnd}` doesn't exist.")
        try:
            await ctx.send(embed=embed)
        except:
            pass


def setup(bot):
    bot.add_cog(Help(bot))

