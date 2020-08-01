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
    
    @commands.command(aliases=['h'])
    async def help(self, ctx, cmnd=None):
        """Display help. \nUsage: help command_name"""
        cogs = ['Moderation', 'Help']
        try:
            if cmnd == None:
                embed=discord.Embed(title="Kurzbot Help", description=f'To see more info do help [command].', color=discord.Color.green())
                for i in cogs:
                    cog = self.bot.get_cog(i)
                    commands = cog.get_commands()
                    commands = ['`' + c.name + '`' for c in commands]
                    embed.add_field(name=i, value='\n'.join(commands))
                
                return await ctx.send(embed=embed)

            elif self.bot.get_command(cmnd).cog_name in cogs:
                command = self.bot.get_command(cmnd)
                embed=discord.Embed(title=command.name, description=f'```{ command.help }```', color=discord.Color.green())
                if command.aliases != []:
                    embed.add_field(name='Alias', value=f'```{ ", ".join(command.aliases) }```', inline=False)
                return await ctx.send(embed=embed)
                
        except Exception as e:
            self.logger.error(str(e))


def setup(bot):
    bot.add_cog(Help(bot))

