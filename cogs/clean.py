import logging

import discord
from discord import message
from discord.ext import commands

import os
import io
import json
import helper
from helper import mod_and_above


class Clean(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Clean')
        self.bot = bot

        config_file = open(os.path.join(os.path.dirname(
            __file__), os.pardir, 'config.json'), 'r')
        self.config_json = json.loads(config_file.read())
        config_file.close()

        self.logging_channel = self.config_json['logging']['logging_channel']

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Clean')

    @commands.command()
    @mod_and_above()
    async def iclean(self, ctx, msg_count: int = None, member: commands.Greedy[discord.Member] = None,
                     channel: discord.TextChannel = None):
        """Command description"""
        try:
            messsage_count = msg_count
            if msg_count is None:
                return await ctx.send(f'**Usage:** `clean number_of_messages <@member(s)/ id(s)> <#channel>`')

            elif msg_count > 200:
                return await ctx.send(f'Provided number is too big. (Max limit 100)')

            elif msg_count <= 0:
                return await ctx.channel.purge(limit=1)

            else:
                if channel is None:
                    channel = ctx.channel

                def check(m):
                    if m.author in member:
                        nonlocal messsage_count
                        messsage_count -= 1
                        if messsage_count >= 0:
                            return True
                    return False

                if not member:
                    deleted_messages = await channel.purge(limit=msg_count + 1)
                else:
                    deleted_messages = await channel.purge(limit=150, check=check)

                await ctx.send(f"Deleted {len(deleted_messages) - 1} message(s)", delete_after=3.0)

                # TODO: Logging of deleted messages
                if msg_count == 1:
                    logging_channel = discord.utils.get(
                        ctx.guild.channels, id=self.logging_channel)

                    embed = helper.create_embed(author=ctx.author, users=None, action='1 message deleted',
                                                extra=f'Message Content: {deleted_messages[-1].content} \nSender: {deleted_messages[-1].author.mention} \nTime: {deleted_messages[-1].created_at.replace(microsecond=0)} \nID: {deleted_messages[-1].id} \nChannel: {channel.mention}',
                                                color=discord.Color.green())

                    await logging_channel.send(embed=embed)

                else:
                    log_str = "Author (ID)".ljust(70) + " | " + "Message Creation Time (UTC)".ljust(
                        30) + " | " + "Content" + "\n\n"

                    for msg in deleted_messages:
                        author = f'{msg.author.name}#{msg.author.discriminator} ({msg.author.id})'.ljust(
                            70)
                        time = f'{msg.created_at.replace(microsecond=0)}'.ljust(
                            30)

                        content = f'{msg.content}'

                        if msg.attachments:
                            content = "Attachment(s): "
                            for a in msg.attachments:
                                content = content + f'{a.filename}' + ", "

                        log_str = log_str + author + " | " + time + " | " + content + "\n"

                    logging_channel = discord.utils.get(
                        ctx.guild.channels, id=self.logging_channel)

                    await logging_channel.send(f'{len(deleted_messages)} messages deleted in {channel.mention}', file=discord.File(io.BytesIO(f'{log_str}'.encode()), filename=f'{len(deleted_messages)} messages deleted in {channel.name}'))

        except Exception as e:
            self.logger.error(str(e))


def setup(bot):
    bot.add_cog(Clean(bot))
