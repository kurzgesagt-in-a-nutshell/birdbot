import os

from traceback import TracebackException

import discord
from discord.ext import commands
from discord.ext.commands import errors


class Errors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, err):
        traceback_text = ''.join(
            TracebackException.from_exception(err).format())
        server = self.bot.get_guild(414027124836532234)
        channel = server.get_channel(414179142020366336)
        print(traceback_text)
        if isinstance(err, errors.MissingRequiredArgument):
            embed = discord.Embed(
                color=0xfa7e8f,
                description=f"You're missing the field of input called "
                            f"`{err.param}` in the `{ctx.command.name}` "
                            f"command. Please check `{ctx.prefix}help`."
            )
            await ctx.send(embed=embed)
        elif isinstance(err, errors.BadArgument):
            embed = discord.Embed(
                color=0xfa7e8f,
                description=f"You seem to have passed in a bad argument"
                            f" for the command `{ctx.command.name}`."
                            f" Please check `{ctx.prefix}help` for more information on how to use the `{ctx.command.name}` command."
            )
            await ctx.send(embed=embed)
        elif isinstance(err, errors.CommandInvokeError):
            if "2000 or fewer" in str(err) and len(ctx.message.clean_content) > 1900:
                embed = discord.Embed(
                    color=0xfa7e8f, description=f"You attempted to make the command display more than 2,000 characters. Both error and command will be ignored.")
                await ctx.send(embed=embed)
                return
            else:
                embed = discord.Embed(
                    color=0xfa7e8f, description=f"There was an unhandled exception that occured. If the issue persists please head to our support server at [this link](https://discord.gg/7rkQ6re)")
                await ctx.send(embed=embed)
                await channel.send(err)
        elif isinstance(err, errors.CheckFailure) or isinstance(err, errors.MissingPermissions):
            try:
                perms = ", ".join(item for item in err.missing_perms)
                perms = perms.replace("_", " ")
                embed = discord.Embed(
                    color=0xfa7e8f, description=f"You don't have the necessary permissions to run this command.\nTo run this command you need `{perms.title()}`.")
                await ctx.send(embed=embed)
            except:
                embed = discord.Embed(
                    color=0xfa7e8f, description=f"You don't have the necessary permissions to run this command.")
                await ctx.send(embed=embed)
            return
        elif isinstance(err, errors.CommandOnCooldown):
            embed = discord.Embed(
                color=0xfa7e8f, description=f"This command is on cooldown. Please try again in `{err.retry_after:.2f}` seconds!")
            await ctx.send(embed=embed)
            return
        elif isinstance(err, errors.CommandNotFound):
            print('Command not found.')
            return
#             embed = discord.Embed(color=0xfa7e8f, description=f"There is no command called `{ctx.command.name}` see `{ctx.prefix}help`")
#             await ctx.send(embed=embed)
        else:
            await channel.send(err)
        tb_file = open(f'tmp_traceback_{ctx.guild.id}.txt', 'w+')
        tb_file.write(traceback_text)
        tb_file.close()
        await channel.send(file=discord.File(f'tmp_traceback_{ctx.guild.id}.txt'))
        os.remove(f'tmp_traceback_{ctx.guild.id}.txt')


def setup(bot):
    bot.add_cog(Errors(bot))
