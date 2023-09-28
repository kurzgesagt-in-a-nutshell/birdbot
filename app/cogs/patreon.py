import asyncio

import discord
from discord import app_commands
from discord.ext import commands

import app.utils.errors as errors
from app.birdbot import BirdBot
from app.utils import checks
from app.utils.config import Reference
from app.utils.infraction import InfractionList


class Patreon(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Listen for new patrons and provide
        them the option to unenroll from autojoining
        Listen for new members and fire webhook for greeting"""

        diff_roles = [role.id for role in member.roles]
        if any(x in diff_roles for x in Reference.Roles.patreon()):
            guild = self.bot.get_mainguild()
            verified = guild.get_role(Reference.Roles.verified)
            english = guild.get_role(Reference.Roles.english)
            assert verified
            assert english
            await member.add_roles(
                verified,
                english,
                reason="Patron auto join",
            )

            try:
                embed = discord.Embed(
                    title="Hey there patron! Annoyed about auto-joining the server?",
                    description="Unfortunately Patreon doesn't natively support a way to disable this- "
                    "but you have the choice of getting volutarily banned from the server "
                    "therby preventing your account from rejoining. To do so simply type ```!unenrol```"
                    "If you change your mind in the future just fill out [this form!](https://forms.gle/m4KPj2Szk1FKGE6F8)",
                    color=0xFFFFFF,
                )
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/824253681443536896.png?size=256")

                await member.send(embed=embed)
            except discord.Forbidden:
                return

    @app_commands.command()
    @checks.patreon_only()
    @app_commands.checks.cooldown(1, 300, key=lambda i: (i.user.id))
    async def unenrol(self, interaction: discord.Interaction):
        """Unenrol from Patron auto join"""

        embed = discord.Embed(
            title="We're sorry to see you go",
            description="Are you sure you want to get banned from the server?"
            "If you change your mind in the future you can simply fill out [this form.](https://forms.gle/m4KPj2Szk1FKGE6F8)",
            color=0xFFCB00,
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/736621027093774467.png?size=96")

        def check(reaction, user):
            return user == interaction.user

        fallback_embed = discord.Embed(
            title="Action Cancelled",
            description="Phew, That was close.",
            color=0x00FFA9,
        )
        confirm_msg: discord.Message | None = None
        try:
            confirm_msg = await interaction.user.send(embed=embed)
            await interaction.response.send_message("Please check your DMs.")
            await confirm_msg.add_reaction(Reference.Emoji.PartialString.kgsYes)
            await confirm_msg.add_reaction(Reference.Emoji.PartialString.kgsNo)
            reaction, user = await self.bot.wait_for("reaction_add", timeout=120, check=check)
            assert isinstance(reaction.emoji, discord.Emoji)

            if reaction.emoji.id == Reference.Emoji.kgsYes:
                member = self.bot.get_mainguild().get_member(interaction.user.id)
                if member == None:
                    raise errors.InvalidFunctionUsage()
                user_infractions = InfractionList.from_user(member)
                user_infractions.banned_patreon = True
                user_infractions.update()

                await interaction.user.send("Success! You've been banned from the server.")
                await member.ban(reason="Patron Voluntary Removal")
                return
            if reaction.emoji.id == Reference.Emoji.kgsNo:
                await confirm_msg.edit(embed=fallback_embed)
                return

        except discord.Forbidden:
            await interaction.response.send_message(
                "I can't seem to DM you. please check your privacy settings and try again",
                ephemeral=True,
            )

        except asyncio.TimeoutError:
            if confirm_msg != None:
                await confirm_msg.edit(embed=fallback_embed)


async def setup(bot: BirdBot):
    await bot.add_cog(Patreon(bot))
