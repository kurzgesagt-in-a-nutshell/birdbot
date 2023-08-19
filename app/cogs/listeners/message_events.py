
import requests, re
from requests.models import PreparedRequest

import discord, io
from discord.ext import commands

from app.utils.helper import is_internal_command
from app.utils.config import Reference

class MessageEvents(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):

        # TODO: we can most likely remove this since we have all transitioned
        # to understanding slash?

        if not message.author.bot:

            guild = discord.utils.get(self.bot.guilds, id=Reference.guild)
            mod_role = discord.utils.get(guild.roles, id=Reference.Roles.moderator)
            admin_role = discord.utils.get(guild.roles, id=Reference.Roles.administrator)

            if not (
                (mod_role in message.author.roles)
                or (admin_role in message.author.roles)
            ):
                return
            if re.match("^-(kick|ban|mute|warn)", message.content):
                await message.channel.send(f"ahem.. {message.author.mention}")
        
        # --- END TODO

        await self.check_mod_alert(message)
        await self.check_server_moments(message)
        await self.translate_bannsystem(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        # Mainbot only, Kgs server only, ignore bot edits
        if (
            self.bot.user.id != Reference.mainbot 
            or before.guild.id != Reference.guild 
            or before.author.bot
        ):
            return

        await self.check_server_moments(after)
        await self.log_message_edit(before, after)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
# Mainbot only, Kgs server only, ignore bot edits
        if (
            self.bot.user.id != Reference.mainbot 
            or message.guild.id != Reference.guild 
            or message.author.bot
            or message.channel.category.id == Reference.Categories.moderation
        ):
            return

        if is_internal_command(self.bot, message):
            return
        
        await self.log_message_delete(message)


    async def log_message_delete(self, message):
        embed = discord.Embed(
            title="Message Deleted",
            description=f"Message deleted in {message.channel.mention}",
            color=0xC9322C,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=message.author.display_name, icon_url=message.author.display_avatar.url
        )
        embed.add_field(name="Content", value=message.content)
        search_terms = f"```Deleted in {message.channel.id}"

        latest_logged_delete = [
            log
            async for log in message.guild.audit_logs(
                limit=1, action=discord.AuditLogAction.message_delete
            )
        ][0]

        self_deleted = False
        if message.author == latest_logged_delete.target:
            embed.description += f"\nDeleted by {latest_logged_delete.user.mention} {latest_logged_delete.user.name}"
            search_terms += f"\nDeleted by {latest_logged_delete.user.id}"
        else:
            self_deleted = True
            search_terms += f"\nDeleted by {message.author.id}"
            embed.description += (
                f"\nDeleted by {message.author.mention} {message.author.name}"
            )

        search_terms += f"\nSent by {message.author.id}"
        search_terms += f"\nMessage from {message.author.id} deleted by {message.author.id if self_deleted else latest_logged_delete.user.id} in {message.channel.id}```"

        embed.add_field(name="Search terms", value=search_terms, inline=False)
        embed.set_footer(
            text="Input the search terms in your discord search bar to easily sort through specific logs"
        )

        message_logging_channel = self.bot.get_channel(
            Reference.Channels.Logging.message_actions
        )
        await message_logging_channel.send(embed=embed)

    async def log_message_edit(self, before, after):
        """
        Logs message edits outside of the moderator category
        """
        
        if (
            before.channel.category.id == Reference.Categories.moderation
            or before.channel.category.id == Reference.Categories.server_logs
            or before.content == after.content
        ):
            return
        
    
        embed = discord.Embed(
            title="Message Edited",
            description=f"Message edited in {before.channel.mention}",
            color=0xEE7600,
            timestamp=discord.utils.utcnow(),
        )
        embed.set_author(
            name=before.author.display_name, icon_url=before.author.display_avatar.url
        )
        embed.add_field(name="Before", value=before.content, inline=False)
        embed.add_field(name="After", value=after.content, inline=False)
        search_terms = f"""
                        ```Edited in {before.channel.id}\nEdited by {before.author.id}\nMessage edited in {before.channel.id} by {before.author.id}```
                        """

        embed.add_field(name="Search terms", value=search_terms, inline=False)
        embed.set_footer(
            text="Input the search terms in your discord search bar to easily sort through specific logs"
        )

        message_logging_channel = self.bot.get_channel(
            Reference.Channels.Logging.message_actions
        )
        await message_logging_channel.send(embed=embed)

    async def check_mod_alert(self, message: discord.Message):
        """
        Checks incoming messages sent by members to check if they have pinged
        the moderator or trainee moderator role. Ignores if the member is a
        moderator+
        """
        
        # Check if message contains a moderator or traine moderator ping
        if not any(
            x in message.raw_role_mentions
            for x in [Reference.Roles.moderator, Reference.Roles.trainee_mod]
        ):
            return

        # If the ping was done by a moderator or above then ignore
        if message.author.top_role >= await message.guild.fetch_role(
            Reference.Roles.moderator
        ):
            return

        # TODO BEFORE COMMIT, LOOK HERE TF DOES ROLE COME FROM?

        role_names = [
            discord.utils.get(message.guild.roles, id=role).name
            for role in message.raw_role_mentions
        ]
        mod_channel = self.bot.get_channel(Reference.Channels.mod_chat)

        embed = discord.Embed(
            title="Mod ping alert!",
            description=f"{' and '.join(role_names)} got pinged in {message.channel.mention} - [view message]({message.jump_url})",
            color=0x00FF00,
        )
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url,
        )
        embed.set_footer(
            text="Last 50 messages in the channel are attached for reference"
        )

        to_file = ""
        async for msg in message.channel.history(limit=50):
            to_file += f"{msg.author.display_name}: {msg.content}\n"

        await mod_channel.send(
            embed=embed,
            file=discord.File(io.BytesIO(to_file.encode()), filename="history.txt"),
        )

    async def check_server_moments(self, message):
        """
        Checks incoming messages to server-moments to validate the have an image
        or is sent by a moderator+
        """
        
        # Return if channel is not server moments
        if message.channel.id != Reference.Channels.server_moments:
            return
        
        # Return if author is a moderator or above
        if any(
            _id in [role.id for role in message.author.roles]
            for _id in Reference.Roles.moderator_and_above
        ):
            return

        # Returns if author is a bot account
        if message.author.bot:
            return
        
        if len(message.attachments) == 0 and len(message.embeds) == 0:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} You can only send screenshots in this channel. ",
                delete_after=5,
            )
            return
        else:
            for e in message.embeds:
                if e.type != "image":
                    await message.delete()
                    await message.channel.send(
                        f"{message.author.mention} You can only send screenshots in this channel. ",
                        delete_after=5,
                    )
                    return
                
    async def translate_bannsystem(self, message: discord.Message):
        """
        Translate incoming bannsystem reports
        """

        if not (
            message.channel.id == Reference.Channels.Logging.bannsystem
            and message.author.id == Reference.bannsystembot
        ):
            return

        embed = message.embeds[0].to_dict()
        to_translate = sum(
            [[embed["description"]], [field["value"] for field in embed["fields"]]], []
        )  # flatten without numpy

        embed["fields"][0]["name"] = "Reason"
        embed["fields"][1]["name"] = "Proof"

        url = "https://translate.birdbot.xyz/translate?"

        # TODO add keys in the future
        payload = {
            "q": " ### ".join(to_translate),
            "target": "en",
            "source": "de",
            "format": "text",
        }

        req = PreparedRequest()
        req.prepare_url(url, payload)
        response = requests.request("POST", req.url, verify=False).json()
        replace_str = response["translatedText"].split(" ### ")
        embed["description"] = replace_str[0]
        embed["fields"][0]["value"] = replace_str[1]
        embed["fields"][1]["value"] = replace_str[2]
        to_send = discord.Embed.from_dict(embed)

        translated_msg = await message.channel.send(embed=to_send)

        await translated_msg.add_reaction("<:kgsYes:955703069516128307>")
        await translated_msg.add_reaction("<:kgsNo:955703108565098496>")
        await message.delete()

    # TODO: Move to slash
    @commands.command()
    async def translate(self, ctx, msg_id):
        msg = await ctx.channel.fetch_message(msg_id)
        embed = await self.translate_bannsystem(msg)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MessageEvents(bot))