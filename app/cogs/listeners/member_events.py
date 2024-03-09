# Copyright (C) 2024, Kurzgesagt Community Devs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import discord
from discord.ext import commands

from app.birdbot import BirdBot
from app.utils.config import Reference


class MemberEvents(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.bot.ismainbot():
            return

        await self.send_welcome(member)
        await self.log_member_join(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not self.bot.ismainbot():
            return

        await self.log_member_remove(member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """
        Grant roles upon passing membership screening
        """

        if not self.bot.ismainbot():
            return

        await self.check_member_screen(before, after)
        await self.log_nickname_change(before, after)

    async def send_welcome(self, member: discord.Member):
        """
        Send welcome message
        """
        new_member_channel = self.bot._get_channel(Reference.Channels.new_members)
        await new_member_channel.send(
            content=f"Welcome hatchling {member.mention}!\n"
            "Make sure to read the <#414268041787080708> and say hello to our <@&584461501109108738>s",
            allowed_mentions=discord.AllowedMentions(users=True, roles=True),
        )

    async def log_member_join(self, member: discord.Member):
        embed = discord.Embed(
            title="Member joined",
            description=f"{member.name}#{member.discriminator} ({member.id}) {member.mention}",
            color=0x45E65A,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)

        embed.add_field(
            name="Account Created",
            value=f"<t:{round(member.created_at.timestamp())}:R>",
            inline=True,
        )

        embed.add_field(name="Search terms", value=f"```{member.id} joined```", inline=False)
        embed.set_footer(text="Input the search terms in your discord search bar to easily sort through specific logs")

        member_logging_channel = self.bot._get_channel(Reference.Channels.Logging.member_actions)
        await member_logging_channel.send(embed=embed)

    async def log_member_remove(self, member: discord.Member):
        embed = discord.Embed(
            title="Member Left",
            description=f"{member.name}#{member.discriminator} ({member.id})",
            color=0xFF0004,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)

        embed.add_field(
            name="Account Created",
            value=f"<t:{round(member.created_at.timestamp())}:R>",
            inline=True,
        )
        embed.add_field(
            name="Joined Server",
            value=f"<t:{round(member.joined_at.timestamp())}:R>" if member.joined_at else "NONE",
            inline=True,
        )
        embed.add_field(
            name="Roles",
            value=f"{' '.join([role.mention for role in member.roles])}",
            inline=False,
        )

        embed.add_field(name="Search terms", value=f"```{member.id} left```", inline=False)
        embed.set_footer(text="Input the search terms in your discord search bar to easily sort through specific logs")

        member_logging_channel = self.bot._get_channel(Reference.Channels.Logging.member_actions)
        await member_logging_channel.send(embed=embed)

    async def check_member_screen(self, before: discord.Member, after: discord.Member):
        if before.pending and (not after.pending):
            guild = self.bot.get_mainguild()
            english = guild.get_role(Reference.Roles.english)
            assert english
            await after.add_roles(
                english,
                reason="Membership screening passed",
            )

    async def log_nickname_change(self, before: discord.Member, after: discord.Member):
        if before.nick == after.nick:
            return

        embed = discord.Embed(
            title="Nickname changed",
            description=f"{before.name}#{before.discriminator} ({before.id})",
            color=0xFF6633,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(name=before.name, icon_url=before.display_avatar.url)
        embed.add_field(name="Previous Nickname", value=f"{before.nick}", inline=True)
        embed.add_field(name="Current Nickname", value=f"{after.nick}", inline=True)

        embed.add_field(
            name="Search terms",
            value=f"```{before.id} changed nickname```",
            inline=False,
        )
        embed.set_footer(text="Input the search terms in your discord search bar to easily sort through specific logs")

        member_logging_channel = self.bot._get_channel(Reference.Channels.Logging.member_actions)
        await member_logging_channel.send(embed=embed)


async def setup(bot: BirdBot):
    await bot.add_cog(MemberEvents(bot))
