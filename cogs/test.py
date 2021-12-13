import logging

import discord
from discord.ext import commands


class Test(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Test')
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Test')
    

    @commands.Cog.listener()
    async def on_message(self, message):
        """Remind mods to use correct prefix, alert mod pings etc"""
        self.logger.info("fired on_message")
        if any(
            x in message.raw_role_mentions
            for x in [414092550031278091, 905510680763969536]
        ):

            self.logger.info("detected mod ping")
            role_names = [
                discord.utils.get(message.guild.roles, id=role).name
                for role in message.raw_role_mentions
            ]
            # mod_channel = self.bot.get_channel(414095428573986816)
            mod_channel = self.bot.get_channel(414179142020366336)
            
            embed = discord.Embed(
                title="Mod ping alert!",
                description=f"{' and '.join(role_names)} got pinged in {message.channel.mention} - [view message]({message.jump_url})",
                color=0x00FF00,
            )
            embed.set_author(
                name=message.author.display_name, icon_url=message.author.avatar_url
            )
            embed.set_footer(
                text="Last 50 messages in the channel are attached for reference"
            )
            self.logger.info("made embed")

            to_file = ""
            async for msg in message.channel.history(oldest_first=True,limit=50):
                to_file += f"{msg.author.display_name}: {msg.content}\n"

            self.logger.info("went through channel history")

            await mod_channel.send(
                embed=embed,
                file=discord.File(io.BytesIO(to_file.encode()),filename="history.txt")
            )

    @commands.command()
    async def your_command(self, ctx):
        """Command description"""
        await ctx.send('thing')
    

def setup(bot):
    bot.add_cog(Test(bot))

