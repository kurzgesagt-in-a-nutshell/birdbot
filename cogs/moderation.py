import logging
import json
import os
import datetime

import sys
sys.path.append('..')
import helper

import discord
from discord.ext import commands

from hastebin_client.utils import *
class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.isdigit():
            member_id = int(argument, base=10)
            try:
                return await ctx.guild.fetch_ban(discord.Object(id=member_id))
            except discord.NotFound:
                raise commands.BadArgument('This member has not been banned before.') from None

        ban_list = await ctx.guild.bans()
        entity = discord.utils.find(lambda u: str(u.user) == argument, ban_list)

        if entity is None:
            raise commands.BadArgument('This member has not been banned before.')
        return entity


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
    
    
    @commands.command(aliases=['purge'])
    @commands.has_guild_permissions(manage_messages=True)
    async def clean(self, ctx, msg_count: int = None, member: discord.Member = None):
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

                logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

                embed = helper.create_embed(author=ctx.author, users=None, action='1 message deleted', reason="None", extra=f'Message Content: { msg[-1].content } \nSender: { msg[-1].author } \nTime: { msg[-1].created_at } \nID: { msg[-1].id }', color=discord.Color.green())
                
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


                logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

                embed = helper.create_embed(author=ctx.author, users=None, action=f'{ msg_count+1 } message(s) deleted', reason="None", extra=cache_file_url, color=discord.Color.green())

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


            logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

            embed = discord.Embed(title=f'**{ msg_count } message(s) deleted**', description="", color=0xff0000)
            embed.add_field(name='Deleted By ', value=f'{ ctx.author.name }#{ ctx.author.discriminator } \n({ ctx.author.id })')
            embed.add_field(name='Channel ', value=f'<#{ ctx.channel.id }>')
            embed.add_field(name='Details ', value=cache_file_url, inline=False)

            await logging_channel.send(embed=embed)

            await ctx.message.delete()


    @commands.command(aliases = ['yeet'])
    @commands.has_permissions(ban_members=True)
    async def ban(self,ctx,member: discord.Member,*,reason: str = None):

        if reason is None:
            return await ctx.send('Please provide a reason')

        logging_channel = discord.utils.get(ctx.guild.channels,id=self.logging_channel)
        await member.ban(reason=reason)
        await ctx.send('Done!')
        
        embed = helper.create_embed(author=ctx.author, users=[member], action='Ban', reason=reason, color=discord.Color.dark_red())

        await logging_channel.send(embed=embed)


    @commands.command()
    @commands.has_guild_permissions(ban_members=True)
    async def unban(self, ctx, member: BannedMember, *, reason: str = None):
        logging_channel = discord.utils.get(ctx.guild.channels,id=self.logging_channel)

        if reason is None:
            reason = f'Action done by {ctx.author} (ID: {ctx.author.id})'

        await ctx.guild.unban(member.user, reason=reason)

        if member.reason:

            embed = helper.create_embed(author=ctx.author, users=[member.user], action='Ban', reason=member.reason, color=discord.Color.dark_red())

            await logging_channel.send(embed=embed)
        else:
            
            embed = helper.create_embed(author=ctx.author, users=[member.user], action='Ban', reason=reason, color=discord.Color.dark_red())

            await logging_channel.send(embed=embed)
        await ctx.send('Done!')


    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self,ctx,members: commands.Greedy[discord.Member],*,reason: str):
        logging_channel = discord.utils.get(ctx.guild.channels,id=self.logging_channel)
        for i in members:
            await i.kick(reason=reason)
        await ctx.send('Done!')

        embed = helper.create_embed(author=ctx.author, users=members, action='Kick', reason=reason, color=discord.Color.red())

        await logging_channel.send(embed=embed)

    
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def mute(self,ctx,members: commands.Greedy[discord.Member],*,reason: str):
        try:
            logging_channel = discord.utils.get(ctx.guild.channels,id=self.logging_channel)
            mute_role = discord.utils.get(ctx.guild.roles, id=681323126252240899)

            for i in members:
                await i.add_roles(mute_role, reason=reason)

            await ctx.send('Done!')
        except Exception as e:
            logging.exception(str(e))
            await ctx.send('Unable to mute users.')


        embed = helper.create_embed(author=ctx.author, users=members, action='Mute', reason=reason, color=discord.Color.red())

        await logging_channel.send(embed=embed)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def unmute(self,ctx,members: commands.Greedy[discord.Member],*,reason: str):
        try: 
            logging_channel = discord.utils.get(ctx.guild.channels,id=self.logging_channel)
            mute_role = discord.utils.get(ctx.guild.roles, id=681323126252240899)
            for i in members:
                await i.remove_roles(mute_role, reason=reason)
            await ctx.send('Done!')
        except Exception as e:
            logging.exception(str(e))
            await ctx.send('Unable to mute users.')
        
        embed = helper.create_embed(author=ctx.author, users=members, action='Unmute', reason=reason, color=discord.Color.red())

        await logging_channel.send(embed=embed)
    


    
def setup(bot):
    bot.add_cog(Moderation(bot))

