import io
import asyncio
import logging
import math
import textwrap
import traceback
import os
import typing

from contextlib import redirect_stdout
from discord.ext.commands.errors import ExtensionNotFound

from git import Repo, exc
from git.cmd import Git

import discord
from discord.ext import commands
from discord import app_commands

from utils import app_checks, helper
from utils.helper import mod_and_above, devs_only, mainbot_only

from utils.config import Reference

class Dev(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Dev")
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Dev")

    def cleanup_code(self, content: str):
        """
        Remove code-block from eval
        """
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        return content.strip("`\n")

    def get_syntax_error(self, e):
        if e.text is None:
            return f"```py\n{e.__class__.__name__}: {e}\n```"
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    @app_commands.command()
    @app_commands.guilds(Reference.guild)
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def activity(
        self,
        interaction: discord.Interaction,
        activity_type: typing.Literal["listening", "watching", "playing"],
        message: str,
    ):
        """Set bot activity status

        Parameters
        ----------
        activity_type: str
            Any of "listening", "watching", "playing"
        message: str
            Message to display after activity_type

        """
        activities = {
            "listening": discord.ActivityType.listening,
            "watching": discord.ActivityType.watching,
            "playing": discord.ActivityType.playing,
        }

        await self.bot.change_presence(
            activity=discord.Activity(name=message, type=activities[activity_type])
        )

        await interaction.response.send_message("Activity changed.", ephemeral=True)

    @commands.is_owner()
    @commands.command(pass_context=True, name="eval")
    async def eval(self, ctx: commands.Context, *, body: str):
        """Evaluates a code"""
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "self": self,
            "math": math,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("<:kgsYes:955703069516128307>")
            except Exception as _:
                await ctx.message.add_reaction("<:kgsNo:955703108565098496>")
                pass

            if ret is None:
                self.logger.info(f"Output chars: {len(str(value))}")
                if value:
                    if len(str(value)) >= 2000:
                        await ctx.send(
                            f"Returned over 2k chars, sending as file instead.\n"
                            f"(first 1.5k chars for quick reference)\n"
                            f"```py\n{value[0:1500]}\n```",
                            file=discord.File(
                                io.BytesIO(value.encode()), filename="output.txt"
                            ),
                        )
                    else:
                        await ctx.send(f"```py\n{value}\n```")
            else:
                self.logger.info(f"Output chars: {len(str(value)) + len(str(ret))}")
                self._last_result = ret
                if len(str(value)) + len(str(ret)) >= 2000:
                    await ctx.send(
                        f"Returned over 2k chars, sending as file instead.\n"
                        f"(first 1.5k chars for quick reference)\n"
                        f'```py\n{f"{value}{ret}"[0:1500]}\n```',
                        file=discord.File(
                            io.BytesIO(f"{value}{ret}".encode()), filename="output.txt"
                        ),
                    )
                else:
                    await ctx.send(f"```py\n{value}{ret}\n```")

    @devs_only()
    @commands.command(name="reload", hidden=True)
    async def reload(self, ctx: commands.Context, *, module_name: str):
        """Reload a module"""
        try:
            try:
                await self.bot.unload_extension(module_name)
            except discord.ext.commands.errors.ExtensionNotLoaded as enl:
                await ctx.send(f"Module not loaded. Trying to load it.", delete_after=6)

            await self.bot.load_extension(module_name)
            await ctx.send("Module Loaded")

        except ExtensionNotFound as enf:
            await ctx.send(
                f"Module not found. Possibly, wrong module name provided.",
                delete_after=10,
            )
        except Exception as e:
            self.logger.error("Unable to load module.")
            self.logger.error("{}: {}".format(type(e).__name__, e))

    @commands.command(hidden=True)
    @mod_and_above()
    async def kill(self, ctx: commands.Context):
        """Kill the bot"""
        await ctx.send("Bravo 6 going dark.")
        await self.bot.close()

    @commands.command(hidden=True)
    @mod_and_above()
    async def restart(self, ctx: commands.Context, instance: str):
        """restarts sub processes"""
        if instance not in ("songbirdalpha", "songbirdbeta", "twitterfeed", "youtubefeed"):
            raise commands.BadArgument("Instance argument must be songbirdalpha, songbirdbeta, twitterfeed, youtubefeed")
        process={
            "songbirdalpha": "songbirda.service",
            "songbirdbeta": "songbirdb.service",
            "twitterfeed": "twitter_feed.service",
            "youtubefeed": "youtube_feed.service"
        }
        try:
            child = await asyncio.create_subprocess_shell("systemctl restart " + process[instance],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            await child.wait()
            await ctx.send("process restarted")
        except Exception as e:
            await ctx.send("could not restart process")
            await ctx.send(e.__str__())

    @devs_only()
    @commands.command(aliases=["logs"], hidden=True)
    async def log(self, ctx: commands.Context, lines: int = 10):
        """View the bot's logs"""
        with open("logs/birdbot.log", "r") as f:
            log = f.readlines()[-lines:]

        log = "".join(log)

        if len(log) > 2000:
            await ctx.send(
                f"Returned over 2k chars, sending as file instead.\n"
                f"(first 1k chars for quick reference)\n"
                f'```py\n{f"{log}"[0:1000]}\n```',
                file=discord.File(io.BytesIO(f"{log}".encode()), filename="log.txt"),
            )
        else:
            await ctx.send(f"```\n{log}\n```")

    @commands.command()
    @commands.is_owner()
    @mainbot_only()
    async def launch(self, ctx: commands.Context, instance: str):
        """Spawn child process of alpha/beta bot instance on the VM, only works on main bot"""

        if instance not in ("alpha", "beta"):
            raise commands.BadArgument("Instance argument must be `alpha` or `beta`")

        try:
            child = await asyncio.create_subprocess_shell(
                "python3 startbot.py --{}".format(instance),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            await ctx.send(
                f"Loaded {instance} instance. Don't forget to kill the instance once you're done to prevent memory leaks"
            )
            await child.wait()

        finally:
            try:
                await ctx.send(f"{instance} instance has been terminated")
                await child.terminate()
            except ProcessLookupError:
                pass

    @devs_only()
    @commands.command(hidden=True)
    async def pull(self, ctx: commands.Context):
        self.logger.info("pulling repository")
        repo = Repo(os.getcwd())  # Get git repo object to check changes
        assert not repo.bare
        if repo.is_dirty():
            return await ctx.send(
                "There are untracked changes on the branch, please resolve them before pulling"
            )

        _g = Git(os.getcwd())
        _g.fetch()
        message = _g.pull("origin", "master")
        await ctx.send(f"```{message}```")

    @app_commands.command()
    @app_commands.default_permissions(manage_messages=True)
    @app_checks.mod_and_above()
    async def send(
        self,
        interaction: discord.Interaction,
        msg: str,
        channel: discord.TextChannel = None,
    ):
        if not channel:
            channel = interaction.channel
        await channel.send(msg)
        await interaction.response.send_message("sent", ephemeral=True)

        logging_channel = discord.utils.get(
            interaction.guild.channels, id=Reference.Channels.Logging.mod_actions
        )
        embed = helper.create_embed(
            author=interaction.user,
            action="ran send command",
            extra="Message sent: {}".format(msg),
            color=discord.Color.blurple(),
        )
        await logging_channel.send(embed=embed)

    @commands.command()
    @devs_only()
    async def sync_apps(self, ctx: commands.Context):

        await ctx.bot.tree.sync()
        await ctx.bot.tree.sync(guild=discord.Object(Reference.guild))
        await ctx.reply("Synced local guild commands")

    @commands.command()
    @devs_only()
    async def clear_apps(self, ctx: commands.Context):

        ctx.bot.tree.clear_commands(guild=discord.Object(Reference.guild))
        ctx.bot.tree.clear_commands(guild=None)
        await ctx.bot.tree.sync(guild=discord.Object(Reference.guild))
        await ctx.bot.tree.sync()

        await ctx.send("cleared all commands")


async def setup(bot):
    await bot.add_cog(Dev(bot))
