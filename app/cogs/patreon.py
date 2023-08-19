import asyncio

from discord import (app_commands, Interaction)
from discord.ext import commands
import discord

from app.utils import checks
from app.utils.infraction import InfractionList
from app.utils.config import Reference

class Patreon(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Listen for new patrons and provide
        them the option to unenroll from autojoining
        Listen for new members and fire webhook for greeting"""


        diff_roles = [role.id for role in member.roles]
        if any(x in diff_roles for x in Reference.Roles.patreon):

            guild = discord.utils.get(self.bot.guilds, id=Reference.guild)
            await member.add_roles(
                guild.get_role(Reference.Roles.verified),  # Verified
                guild.get_role(Reference.Roles.english),  # English
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
                embed.set_thumbnail(
                    url="https://cdn.discordapp.com/emojis/824253681443536896.png?size=256"
                )

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
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/emojis/736621027093774467.png?size=96"
        )

        def check(reaction, user):
            return user == interaction.user

        fallback_embed = discord.Embed(
            title="Action Cancelled",
            description="Phew, That was close.",
            color=0x00FFA9,
        )

        try:
            confirm_msg = await interaction.user.send(embed=embed)
            await interaction.response.send_message("Please check your DMs.")
            await confirm_msg.add_reaction("<:kgsYes:955703069516128307>")
            await confirm_msg.add_reaction("<:kgsNo:955703108565098496>")
            reaction, user = await self.bot.wait_for(
                "reaction_add", timeout=120, check=check
            )

            if reaction.emoji.id == Reference.Emoji.kgsYes:

                member = discord.utils.get(
                    self.bot.guilds, id=Reference.guild
                ).get_member(interaction.user.id)

                user_infractions = InfractionList.from_user(member)
                user_infractions.banned_patreon = True
                user_infractions.update()

                await interaction.user.send(
                    "Success! You've been banned from the server."
                )
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
            await confirm_msg.edit(embed=fallback_embed)

async def setup(bot):
    await bot.add_cog(Patreon(bot))