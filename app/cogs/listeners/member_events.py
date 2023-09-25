import random

import aiohttp
import discord
from discord.ext import commands

from app.utils.config import Reference
from app.birdbot import BirdBot


class MemberEvents(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.bot = bot
        self.pfp_list = [
            "https://cdn.discordapp.com/emojis/909047588160942140.png?size=256",
            "https://cdn.discordapp.com/emojis/909047567030059038.png?size=256",
            "https://cdn.discordapp.com/emojis/909046980599250964.png?size=256",
            "https://cdn.discordapp.com/emojis/909047000253734922.png?size=256",
        ]
        self.greeting_webhook_url = "https://discord.com/api/webhooks/909052135864410172/5Fky0bSJMC3vh3Pz69nYc2PfEV3W2IAwAsSFinBFuUXXzDc08X5dv085XlLDGz3MmQvt"

    @commands.Cog.listener()
    async def on_member_join(self, member):

        if self.bot.user.id != Reference.mainbot:
            return

        await self.send_welcome(member)
        await self.log_member_join(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member):

        if self.bot.user.id != Reference.mainbot:
            return

        await self.log_member_remove(member)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """
        Grant roles upon passing membership screening
        """

        if self.bot.user.id != Reference.mainbot:
            return

        await self.check_member_screen(before, after)
        await self.log_nickname_change(before, after)

    async def send_welcome(self, member):
        """
        Send welcome message
        """
        async with aiohttp.ClientSession() as session:
            hook = discord.Webhook.from_url(
                self.greeting_webhook_url,
                session=session,
            )
            await hook.send(
                f"Welcome hatchling {member.mention}!\n"
                "Make sure to read the <#414268041787080708> and say hello to our <@&584461501109108738>s",
                avatar_url=random.choice(self.pfp_list),
                allowed_mentions=discord.AllowedMentions(users=True, roles=True),
            )

    async def log_member_join(self, member):

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

        member_logging_channel = self.bot.get_channel(Reference.Channels.Logging.member_actions)
        await member_logging_channel.send(embed=embed)

    async def log_member_remove(self, member):
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
            value=f"<t:{round(member.joined_at.timestamp())}:R>",
            inline=True,
        )
        embed.add_field(
            name="Roles",
            value=f"{' '.join([role.mention for role in member.roles])}",
            inline=False,
        )

        embed.add_field(name="Search terms", value=f"```{member.id} left```", inline=False)
        embed.set_footer(text="Input the search terms in your discord search bar to easily sort through specific logs")

        member_logging_channel = self.bot.get_channel(Reference.Channels.Logging.member_actions)
        await member_logging_channel.send(embed=embed)

    async def check_member_screen(self, before, after):
        if before.pending and (not after.pending):
            guild = discord.utils.get(self.bot.guilds, id=Reference.guild)
            await after.add_roles(
                guild.get_role(Reference.Roles.verified),  # Verified
                guild.get_role(Reference.Roles.english),  # English
                reason="Membership screening passed",
            )

    async def log_nickname_change(self, before, after):
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

        member_logging_channel = self.bot.get_channel(Reference.Channels.Logging.member_actions)
        await member_logging_channel.send(embed=embed)


async def setup(bot: BirdBot):
    await bot.add_cog(MemberEvents(bot))
