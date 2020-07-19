import logging
import json
import os
import datetime

import typing
import sys
sys.path.append('..')
import helper

import discord
from discord.ext import commands

from hastebin_client.utils import *
import asyncio
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
    async def clean(self, ctx, msg_count: int = None, member: commands.Greedy[discord.Member] = None, channel: discord.TextChannel = None):
        """ Clean messages | Usage: clean number_of_messages <@member> """
        if msg_count is None:
            await ctx.send(f' **Enter number of messages** (k!clean message_count <@member>) ')
        
        elif msg_count > 200:
            await ctx.send(f'Provided number is too big. (Max limit 200)')

        elif msg_count == 0:
            await ctx.channel.purge(limit=1)
        
        if channel is None:
            channel = ctx.channel

        if member is None:
            if msg_count == 1:
                msg = await channel.purge(limit=2)

                logging_channel = discord.utils.get(ctx.guild.channels, id=self.logging_channel)

                embed = helper.create_embed(author=ctx.author, users=None, action='1 message deleted', reason="None", extra=f'Message Content: { msg[-1].content } \nSender: { msg[-1].author } \nTime: { msg[-1].created_at } \nID: { msg[-1].id } \nChannel: #{ channel }', color=discord.Color.green())
                
                await logging_channel.send(embed=embed)
                

            else:
                deleted_msgs = await channel.purge(limit=msg_count+1)

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

                embed = helper.create_embed(author=ctx.author, users=None, action=f'{ msg_count+1 } messages deleted', reason="None", extra=cache_file_url + f'\nChannel: #{ channel }', color=discord.Color.green())

                await logging_channel.send(embed=embed)

        else:

            deleted_msgs = []
            count = msg_count 
            async for m in channel.history(limit=200, oldest_first=False):
                if ctx.message.id == m.id:
                    continue

                deleted_msgs.append(m)
                for mem in member:
                    if m.author.id == mem.id:
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

            embed = helper.create_embed(author=ctx.author, users=member, action=f'{ msg_count } messages deleted', reason="None", extra=cache_file_url + f'\nChannel: #{ channel }', color=discord.Color.green())


            await logging_channel.send(embed=embed)

            await ctx.message.delete()


    @commands.command(aliases = ['yeet'])
    @commands.has_permissions(ban_members=True)
    async def ban(self,ctx,member: discord.Member,*,reason: str = None):
        """ Ban a member. | Usage: ban @member reason """

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
        """ Unban a member. | Usage: unban member_id reason """

        logging_channel = discord.utils.get(ctx.guild.channels,id=self.logging_channel)

        if reason is None:
            reason = f'Action done by {ctx.author} (ID: {ctx.author.id})'

        await ctx.guild.unban(member.user, reason=reason)

        if member.reason:
            embed = helper.create_embed(author=ctx.author, users=[member.user], action='Unban', reason=member.reason, color=discord.Color.dark_red())
            await logging_channel.send(embed=embed)
        else:
            embed = helper.create_embed(author=ctx.author, users=[member.user], action='Unban', reason=reason, color=discord.Color.dark_red())
            await logging_channel.send(embed=embed)
        await ctx.send('Done!')


    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self,ctx,members: commands.Greedy[discord.Member],*,reason: str):
        """ Kick member(s). | Usage: kick @member(s) reason """

        logging_channel = discord.utils.get(ctx.guild.channels,id=self.logging_channel)
        for i in members:
            await i.kick(reason=reason)
        await ctx.send('Done!')

        embed = helper.create_embed(author=ctx.author, users=members, action='Kick', reason=reason, color=discord.Color.red())

        await logging_channel.send(embed=embed)


    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def mute(self,ctx,members: commands.Greedy[discord.Member], time: typing.Optional[str] = None, *, reason=None):
        """ Mute member(s). | Usage: mute @member(s) <time> reason """

        try:
            logging_channel = discord.utils.get(ctx.guild.channels,id=self.logging_channel)
            mute_role = discord.utils.get(ctx.guild.roles, id=681323126252240899)

            try:

                if members == []:
                    return await ctx.send('Provide member(s) to mute.')

                if reason is None and time is None :
                    return await ctx.send('Enter reason.')

                if reason is None:
                    reason = time
                    time = None

                tot_time = 0
                if time is not None:
                    t = 0
                    j = 0
                    for i in time:
                        
                        if i.isdigit():
                            t = t * pow(10, j) + int(i)
                            j = j + 1
                        
                        else:
                            if i == 'd' or i == 'D':
                                tot_time = tot_time + t * 24 * 60 * 60
                            elif i == 'h' or i == 'H':
                                tot_time = tot_time + t * 60 * 60
                            elif i == 'm' or i == 'M':
                                tot_time = tot_time + t * 60
                            elif i == 's' or i == 'S':
                                tot_time = tot_time + t

                            t = 0
                            j = 0
            except Exception as ex:
                self.logger.exception(ex.__str__())     

            
            for i in members:
                await i.add_roles(mute_role, reason=reason)

            await ctx.send('Done!')
        except Exception as e:
            self.logger.exception(str(e))
            await ctx.send('Unable to mute users.')


        embed = helper.create_embed(author=ctx.author, users=members, action='Mute', reason=reason, extra=f'Mute Duration: { time } or { tot_time } seconds' ,color=discord.Color.red())

        await logging_channel.send(embed=embed)

        if time is not None:
            await asyncio.sleep(tot_time)
            await self.unmute(ctx=ctx, members=members, reason=reason)


    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def unmute(self,ctx,members: commands.Greedy[discord.Member],*,reason: str = None):
        """ Unmute member(s). | Usage: unmute @member(s) <reason> """

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
    


    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, members: commands.Greedy[discord.Member], *, role_name: str = None):
        """ Add a role to member(s). | Usage: addrole @member(s) role_name """

        logging_channel = discord.utils.get(ctx.guild.channels,id=self.logging_channel)

        try:

            if role_name is None:
                return await ctx.send('Please enter role name.')

            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if role is None:
                return await ctx.send('Role not found')
            if ctx.author.top_role < role:
                await ctx.send(f'Your role is lower than { role.name }.')
            else:
                for member in members:
                    await member.add_roles(role)

                embed = helper.create_embed(author=ctx.author, users=members, action='Give role', reason="None", extra=f'Role: { role.name }\nRole ID: {role.id}', color=discord.Color.purple())
                await logging_channel.send(embed=embed)

        except Exception as e:
            self.logger.error(str(e))
            await ctx.send('Unable to give role.')
    
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def remrole(self, ctx, members: commands.Greedy[discord.Member], *, role: discord.Role):
        """ Remove a role to member(s). | Usage: remrole @member(s) role_name """
        
        logging_channel = discord.utils.get(ctx.guild.channels,id=self.logging_channel)

        try:
            if ctx.author.top_role < role:
                await ctx.send(f"Your role is lower than {role}.")
            else:
                for member in members:
                    await member.remove_roles(role)

                embed = helper.create_embed(author=ctx.author, users=members, action='Remove role', reason="None", extra=f'Role: {role}\nRole ID: {role.id}', color=discord.Color.purple())
                await logging_channel.send(embed=embed)

        except: 
            await ctx.send('Unable to remove role.')
        

    @commands.command(hidden=True)
    @commands.has_permissions(kick_members=True)
    async def t(self, ctx, time: typing.Optional[str] = None, *, reason=None):
        try:

            if reason is None and time is None :
                return await ctx.send('enter reason')

            if reason is None:
                reason = time
                time = None

            tot_time = 0
            if time is not None:
                t = 0
                j = 0
                for i in time:
                    
                    if i.isdigit():
                        t = t * pow(10, j) + int(i)
                        j = j + 1
                    
                    else:
                        if i == 'd' or i == 'D':
                            tot_time = tot_time + t * 24 * 60 * 60
                        elif i == 'h' or i == 'H':
                            tot_time = tot_time + t * 60 * 60
                        elif i == 'm' or i == 'M':
                            tot_time = tot_time + t * 60
                        elif i == 's' or i == 'S':
                            tot_time = tot_time + t

                        t = 0
                        j = 0

            await ctx.send(tot_time.__str__() + " is time in seconds")
            await ctx.send(reason.__str__() + " is the reason")
            
        except Exception as e:
            logging.error(str(e))
            await ctx.send('Unable to mute users.')


def setup(bot):
    bot.add_cog(Moderation(bot))

