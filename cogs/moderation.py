import logging
import json
import os
from datetime import datetime

from hastebin_client.utils import *

import discord
from discord.member import Member
from discord.ext import commands
from discord.utils import get
from discord.message import Embed


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Moderation')
        self.bot = bot

        config_file = open(os.path.join(os.path.dirname(__file__), os.pardir, 'config.json'), 'r')
        config_json = json.loads(config_file.read())

        self.logging_channel = config_json['logging']['logging-channel']
        self.hastebin_URL = config_json['logging']['hastebin-url']
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Moderation')
    
    
    # FIXME command grouping/alias causes error (TypeError: Callback is already a command.)
    # @commands.group(aliases=['purge'])
    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def clean(self, ctx, msg_count: int = None, member:Member = None):
        """ Clean messages """
        if msg_count is None:
            await ctx.send(f' **Enter number of messages** (k!clean message_count <@member>) ')
        
        elif msg_count > 200:
            await ctx.send(f'Provided number is too big. (Max limit 200)')

        elif msg_count == 0:
            await ctx.channel.purge(limit=1)
        

        if member is None:
            if msg_count == 1:
                msg = await ctx.channel.purge(limit=2)

                logging_channel = get(ctx.guild.channels, id=self.logging_channel)

                embed = Embed(title=f'**1 message deleted**', description="", color=0xff0000)
                embed.add_field(name='Deleted By ', value=f'{ ctx.author.name }#{ ctx.author.discriminator } \n({ ctx.author.id })')
                embed.add_field(name='Channel ', value=f'<#{ ctx.channel.id }>')
                embed.add_field(name='Message ', value=f'```Content: { msg[-1].content } \nSender: { msg[-1].author } \nTime: { msg[-1].created_at } \nID: { msg[-1].id }```', inline=False)

                await logging_channel.send(embed=embed)
                

            else:
                deleted_msgs = await ctx.channel.purge(limit=msg_count+1)

                try:
                    haste_data = "Author (ID)".ljust(70) + " | " + "Message Creation Time (UTC)".ljust(30) + " | " + "Content" + "\n\n"
                    for msg in deleted_msgs:

                        author = f'{ msg.author.name }#{ msg.author.discriminator } ({ msg.author.id })'.ljust(70)
                        time = f'{ msg.created_at }'.ljust(30)
                        content = f'{ msg.content }'
                        haste_data = haste_data + author + " | " + time + " | " + content + "\n"
                        
                    key = upload(haste_data)
                    cache_file_url = create_url(key) + ".txt"

                except ValueError as ve:
                    cache_file_url = str(ve)
                    self.logger.error(str(ve))

                except Exception as e:
                    cache_file_url = str(e)
                    self.logger.error(str(e))


                logging_channel = get(ctx.guild.channels, id=self.logging_channel)

                embed = Embed(title=f'**{ msg_count+1 } message(s) deleted**', description="", color=0xff0000)
                embed.add_field(name='Deleted By ', value=f'{ ctx.author.name }#{ ctx.author.discriminator } \n({ ctx.author.id })')
                embed.add_field(name='Channel ', value=f'<#{ ctx.channel.id }>')
                embed.add_field(name='Details ', value=cache_file_url, inline=False)

                await logging_channel.send(embed=embed)

        else:

            deleted_msgs = []
            count = msg_count 
            async for m in ctx.channel.history(limit=100, oldest_first=False):
                if ctx.message.id == m.id:
                    continue
                deleted_msgs.append(m)
                if m.author.id == member.id:
                    count = count - 1
                    await m.delete()
                if count <= 0:
                    break


            try:
                haste_data = "Author (ID)".ljust(70) + " | " + "Message Creation Time (UTC)".ljust(30) + " | " + "Content" + "\n\n"
                for msg in deleted_msgs:

                    author = f'{ msg.author.name }#{ msg.author.discriminator } ({ msg.author.id })'.ljust(70)
                    time = f'{ msg.created_at }'.ljust(30)
                    content = f'{ msg.content }'
                    haste_data = haste_data + author + " | " + time + " | " + content + "\n"
                    
                key = upload(haste_data)
                cache_file_url = create_url(key) + ".txt"

            except ValueError as ve:
                cache_file_url = str(ve)
                self.logger.error(str(ve))

            except Exception as e:
                cache_file_url = str(e)
                self.logger.error(str(e))


            logging_channel = get(ctx.guild.channels, id=self.logging_channel)

            embed = Embed(title=f'**{ msg_count } message(s) deleted**', description="", color=0xff0000)
            embed.add_field(name='Deleted By ', value=f'{ ctx.author.name }#{ ctx.author.discriminator } \n({ ctx.author.id })')
            embed.add_field(name='Channel ', value=f'<#{ ctx.channel.id }>')
            embed.add_field(name='Details ', value=cache_file_url, inline=False)

            await logging_channel.send(embed=embed)

            await ctx.message.delete()


def setup(bot):
    bot.add_cog(Moderation(bot))

