import re
import asyncio
import traceback

import discord
from discord.ext import commands


class Moderation(commands.Cog, name='Moderation'):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('loaded moderation')

    @commands.command()
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Ban a member from the guild"""
        if ctx.author.top_role < member.top_role:
            return await ctx.send("Your role isn't high enough to complete that action.")
        await member.ban(reason=reason)
        await ctx.send(f"**Banned {member} for reason** `{reason}`.")

    @commands.command()
    @commands.has_guild_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Kick a user from the guild"""
        if ctx.author.top_role < member.top_role:
            return await ctx.send("Your role isn't high enough to complete that action.")
        await member.kick(reason=reason)
        await ctx.send(f"\U0001f9b6 **Kicked {member} for reason** `{reason}`.")

    @commands.command()
    @commands.has_guild_permissions(ban_members=True)
    async def unban(self, ctx, *, member):
        """Unban a user
        Unban a user from the server."""
        banned_users = await ctx.guild.bans()
        member_name, member_discriminator = member.split('#')

        for ban_entry in banned_users:
            user = ban_entry.user

        if(user.name, user.member_discriminator) == (member_name, member_discriminator):
            try:
                await ctx.guild.unban(user)
            except Exception as e:
                await ctx.send(f'Cannot unban user {member.mention} ({member})')
                print(traceback.TracebackException.from_exception(e).format())
            await ctx.channel.send(f'Unbanned {member.mention}')

    @commands.group(aliases=['purge'])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def prune(self, ctx):
        """ Removes messages from the current server. """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(str(ctx.command))

    async def do_removal(self, ctx, limit, predicate, *, before=None, after=None, message=True):
        if limit > 2000:
            embed = discord.Embed(color=0xfa7e8f, description=f"Too many messages to deleted given. `({limit}/2000)`")
            return await ctx.send(embed=embed)

        if before is None:
            before = ctx.message
        else:
            before = discord.Object(id=before)

        if after is not None:
            after = discord.Object(id=after)

        try:
            deleted = await ctx.channel.purge(limit=limit, before=before, after=after, check=predicate)
        except discord.Forbidden:
            embed = discord.Embed(color=0xfa7e8f, description="Permission Error")
            return await ctx.send(embed=embed)
        except discord.HTTPException as e:
            embed = discord.Embed(color=0xfa7e8f, description=f"IError: {e} (try a smaller search?)")
            return await ctx.send(embed=embed)

        deleted = len(deleted)
        if message is True:
            plural = "" if deleted == 1 else "s"
            embed = discord.Embed(colour=0xc3fa7e, description=f"Cleaned `{deleted}` message{plural}!")

            embed.set_footer(text=f"Cleaned by {ctx.author}", icon_url=ctx.author.avatar_url)

            await ctx.send(embed=embed, delete_after = 5)

    @prune.command()
    async def embeds(self, ctx, search=100):
        """Removes messages that have embeds in them."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds))

    @prune.command()
    async def files(self, ctx, search=100):
        """Removes messages that have attachments in them."""
        await self.do_removal(ctx, search, lambda e: len(e.attachments))

    @prune.command()
    async def mentions(self, ctx, search=100):
        """Removes messages that have mentions in them."""
        await self.do_removal(ctx, search, lambda e: len(e.mentions) or len(e.role_mentions))

    @prune.command()
    async def images(self, ctx, search=100):
        """Removes messages that have embeds or attachments."""
        await self.do_removal(ctx, search, lambda e: len(e.embeds) or len(e.attachments))

    @prune.command(name='all')
    async def _remove_all(self, ctx, search=100):
        """Removes all messages."""
        await self.do_removal(ctx, search, lambda e: True)

    @prune.command()
    async def user(self, ctx, member: discord.Member, search=100):
        """Removes all messages by the member."""
        await self.do_removal(ctx, search, lambda e: e.author == member)

    @prune.command()
    async def contains(self, ctx, *, substr: str):
        """Removes all messages containing a substring.
        The substring must be at least 3 characters long.
        """
        if len(substr) < 3:
            await ctx.send('The substring length must be at least 3 characters.')
        else:
            await self.do_removal(ctx, 100, lambda e: substr in e.content)

    @prune.command(name='bots')
    async def _bots(self, ctx, search=100, prefix=None):
        """Removes a bot user's messages and messages with their optional prefix."""

        getprefix = prefix if prefix else self.prefix[str(ctx.guild.id)]

        def predicate(m):
            return (m.webhook_id is None and m.author.bot) or m.content.startswith(tuple(getprefix))

        await self.do_removal(ctx, search, predicate)

    @prune.command(name='users')
    async def _users(self, ctx, prefix=None, search=100):
        """Removes only user messages. """

        def predicate(m):
            return m.author.bot is False

        await self.do_removal(ctx, search, predicate)

    @prune.command(name='emojis')
    async def _emojis(self, ctx, search=100):
        """Removes all messages containing custom emoji."""
        custom_emoji = re.compile(r'<a?:(.*?):(\d{17,21})>|[\u263a-\U0001f645]')

        def predicate(m):
            return custom_emoji.search(m.content)

        await self.do_removal(ctx, search, predicate)

    @prune.command(name='reactions')
    async def _reactions(self, ctx, search=100):
        """Removes all reactions from messages that have them."""

        if search > 2000:
            return await ctx.send(f'Too many messages to search for ({search}/2000)')

        total_reactions = 0
        async for message in ctx.history(limit=search, before=ctx.message):
            if len(message.reactions):
                total_reactions += sum(r.count for r in message.reactions)
                await message.clear_reactions()

        plural = "" if total_reactions == 1 else "s"
        embed = discord.Embed(colour=0xc3fa7e, description=f"Cleaned `{total_reactions}` message{plural}!")

        embed.set_footer(text=f"Cleaned by {ctx.author}", icon_url=ctx.author.avatar_url)

        await ctx.send(embed=embed, delete_after = 7)

        plural = "" if total_reactions == 1 else "s"
        embed = discord.Embed(colour=0xc3fa7e, description=f"Successfully cleaned `{total_reactions}` message{plural}!")

        embed.set_footer(text=f"Clearing in 5s", icon_url=ctx.author.avatar_url)

        await ctx.send(embed=embed, delete_after = 5)

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.command()
    async def mute(self, ctx, member: discord.Member, time: int = 0, *, reason=None):
        """Mute a user.
        member can be mention or userid. Time defaults to infinity."""
        await ctx.message.delete()
        if not member:
            embed = discord.Embed(
                color=0xfa6579, description='Please specify a user to mute.')
            await ctx.send(embed=embed)
            return
        if ctx.author.top_role < member.top_role:
            embed = discord.Embed(
                color=0xfa7e8f, description="Your role isn't high enough to complete that action.")
            return await ctx.send(embed=embed)
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if role is None:
            embed = discord.Embed(
                color=0xfa6579, description="There's no role in the server that's called `Muted`. Please create one before running this command again!")
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/683594544515776545/700779562518446141/RXskOuIiAg.gif")
            await ctx.send(embed=embed)
        await member.add_roles(role)
        embed = discord.Embed(title="Member Muted", color=0xc3fa7e)
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/avatars/{0.id}/{0.avatar}.png?size=1024".format(member))
        embed.add_field(name="User:", value=member, inline=False)
        embed.add_field(name="Duration (minutes):", value=time, inline=False)
        embed.add_field(name="Reason:", value=reason, inline=False)
        embed.add_field(name="Moderator:",
                        value=ctx.message.author, inline=False)
        await ctx.send(embed=embed)
        if time > 0:
            await asyncio.sleep(time * 60)
            await member.remove_roles(role)

    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_roles=True)
    @commands.command()
    async def unmute(self, ctx, member: discord.Member = None):
        """Unmute a user."""
        await ctx.channel.purge(limit=1)
        if not member:
            embed = discord.Embed(
                color=0xfa6579, description='Please specify a user to unmute.')
            await ctx.send(embed=embed)
            return
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        await member.remove_roles(role)
        bruh = await self.bot.fetch_user(member.id)
        embed = discord.Embed(title="Member Umuted", color=0xc3fa7e)
        embed.set_thumbnail(url=bruh.avatar_url)
        embed.add_field(name="User:", value=member, inline=False)
        embed.add_field(name="Moderator:",
                        value=ctx.message.author, inline=False)
        await ctx.send(embed=embed)

    @commands.has_permissions(manage_roles=True)
    @commands.command()
    async def addrole(self, ctx, member: discord.Member, *, role: discord.Role):
        """Add a role to a user"""
        try:
            if ctx.author.top_role < role:
                embed = discord.Embed(
                    color=0xfa7e8f, description="Your role isn't high enough to complete that action.")
                return await ctx.send(embed=embed)
            await member.add_roles(role)
        except Exception as e:
            embed = discord.Embed(
                color=0xfa6579, description='Unable to add the role `{}` to `{}`.'.format(role, member))
            await ctx.send(embed=embed)
            print(''.join(traceback.TracebackException.from_exception(e).format()))
        else:
            embed = discord.Embed(
                color=0xc3fa7e, description="Successfully added `{}` to `{}`.".format(role, member))
            await ctx.send(embed=embed)

    @commands.has_permissions(manage_roles=True)
    @commands.command()
    async def delrole(self, ctx, member: discord.Member, *, role: discord.Role):
        """Remove a role from a user."""
        try:
            if ctx.author.top_role < role:
                embed = discord.Embed(
                    color=0xfa7e8f, description="Your role isn't high enough to complete that action.")
                return await ctx.send(embed=embed)
            await member.remove_roles(role)
        except Exception as e:
            embed = discord.Embed(
                color=0xfa6579, description='Unable to remove the role `{}` to `{}`.'.format(role, member))
            await ctx.send(embed=embed)
            print(''.join(traceback.TracebackException.from_exception(e).format()))
        else:
            embed = discord.Embed(
                color=0xc3fa7e, description="Successfully removed `{}` from `{}`.".format(role, member))
            await ctx.send(embed=embed)

    @commands.has_permissions(manage_roles=True)
    @commands.command()
    async def createrole(self, ctx, *, role_name: str):
        """Create a role in the server.
        Example: createrole dumb role"""
        await ctx.guild.create_role(name=role_name, reason=f'By user: {ctx.author}')
        embed = discord.Embed(
            color=0xc3fa7e, description=f"Added `{role_name}`")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Moderation(bot))
