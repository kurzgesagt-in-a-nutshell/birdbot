import logging
logging.basicConfig(level=logging.INFO)
import discord,asyncio,time,random,typing
from itertools import cycle
from discord.ext import commands
cboard=['1','2','3','4','5','6','7','8','9']
pl1='X'
pl2='O'
prefix = 'k!'
bot = commands.Bot(command_prefix=prefix)
token = 'NDcxNzA1NzE4OTU3ODAxNDgz.XN7cLw.ntikeK86SgIq58QCw4_apMPfI30'

@bot.command()    
async def board(ctx):
	embed=discord.Embed(title="{}".format("Player X:  "),description=("  {}  |  {}  |  {}  \n{}  |  {}  |  {}\n{}  |  {}  |  {}\n").format(*cboard))
	rm=bot.get_channel(482936367043837976)
	await rm.send(embed=embed)

async def mod_admin_shuffle():
    await bot.wait_until_ready()
    kurz_server = bot.get_guild(414027124836532234)
    moderators = kurz_server.get_role(414092550031278091)
    admins = kurz_server.get_role(414029841101225985)
    mod_admin_set=set(moderators.members+admins.members)
    mod_admin_list=[]
    
    for members in mod_admin_set:
        if members.status != discord.Status.offline:
            mod_admin_list.append(members)
            
    while bot.is_ready():
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name=random.choice(mod_admin_list)))
        await asyncio.sleep(700)
    


@bot.command()
@commands.is_owner()
#@commands.has_any_role(414092550031278091,414029841101225985,414954904382210049)
async def ban(ctx,members: commands.Greedy[discord.Member],delete_messages: typing.Optional[int]=0,*,reason: str):
    for member in members:
        await member.ban(delete_message_days=delete_messages,reason=reason)
    await ctx.send("**Banned!** {} for {}".format(member,reason))
        
@ban.error
async def ban_error(ctx,error):
    if isinstance(error,commands.MissingAnyRole):
        await ctx.send('You are not authorized to perform this action')
    
@bot.command()
@commands.has_any_role(414092550031278091,414029841101225985,414954904382210049)
async def send(ctx,channel: discord.TextChannel,*,msg):
    channel_subs = channel
    await channel.send(msg)
    print("sent the following message to channel : {}\n".format(channel_subs))
    print(msg)
    
@send.error
async def send_error(ctx,error):
    if isinstance(error,commands.MissingAnyRole):
        await ctx.send('You are not authorized to perform this action')
        
def ping_format():
    latency_ms=bot.latency*1000
    ping_embed=discord.Embed(title="\U0001f3d3 You asked for my ping? \U0001f3d3",description='**Ping Pong**\n**Latency: {}ms**'.format(round(latency_ms,3)))
    return ping_embed
    
@bot.command()
async def ping(ctx):
    await ctx.send(embed=ping_format(),delete_after=15.0)
    await ctx.message.delete(delay=1.0)



@bot.command()
@commands.is_owner()
async def presence(ctx,action,*,arg2):
    taskobj.cancel()
    if action=='p':
        await ctx.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing,name=arg2))
        await ctx.message.add_reaction('\U00002705')
        print('presence updated: playing ' + arg2)
    if action=='w':
        await ctx.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name=arg2))
        await ctx.message.add_reaction('\U00002705')
        print('presence updated: watching ' + arg2)
    if action=='l':
        await ctx.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name=arg2))
        await ctx.message.add_reaction('\U00002705')
        print('presence updated: listening to ' + arg2)
        
@presence.error
async def presence_error(ctx,error):
    if isinstance(error,commands.CheckFailure):
        await ctx.send("You are not authorized to perform this action")

  
          
embed = discord.Embed(title="RULES",description=":one: This is the rules page. Read it.\n:two: No defamation, bullying, harassment, or any other act of the like.\n:three: No advertising\n:four: No impersonating others, especially Kurzgesagt officials.\n:five: No spam (this includes emojis and pings)\n:six: No NSFW content.\n:seven: Don’t ping mods unnecessarily.\n:eight: The admins and moderators of this server are **NOT** a part of the Kurzgesagt team, unless stated otherwise by their role.\n:nine: Do not ask admins or moderators about Kurzgesagt’s upload schedule/topic (put simply, we don’t know).\n:one::zero: Staff ultimately have the final say in how severe a punishment may be. Some crimes are worse than others.\n:one::one: Rules maybe updated and subjected to change over time, so refresh your knowledge every once in a while.\n:one::two: Once you're done reading the rules type    ```!accept``` in <#526882555174191125>",color=0x45c4ff)
embed.set_footer(text="As of 7;45AM UTC 24th August 2019",icon_url = 'https://cdn.discordapp.com/attachments/414179142020366336/564341337315475456/gtr.png')
embed.add_field(name="PUNISHMENT",value="**1st offense:** Warning\n**2nd offense:** 48 hour mute\n**3rd offense:** ban\nStaff have the right to deem some offenses worthy of 2 or more warnings.Leaving the server and rejoining to remove offenses on your record/get out of jail will result in a PERMANENT BAN without appeal.",inline=False)
embed.add_field(name='REWARDS',value=':one: Those who make significant contributions to either the discord or Kurzgesagt itself are able to receive the <@&476852559311798280> role. \n:two: Donators and Patrons of Kurzgesagt (i.e., a monetary contribution) will receive the <@&415154206970740737> role.\n:three: Users who Nitro boost the server receive the<@&598031301622104095> role \n:four: Those who are not donators/Contributors, a series of colours are free for you to pick from in <#558333807548432395>',inline=False)   
embed.set_thumbnail(url='https://cdn.discordapp.com/attachments/522777063376158760/569234678540926997/orbit.gif')

#rolemenu=discord.Embed(title="React to get a role",description="\n:regional_indicator_v:**:Violet Bird**\n\n:regional_indicator_p:**: Pink Bird**\n\n:regional_indicator_b:**: Blue Bird**\n\n:regional_indicator_g:**: Green Bird**\n\n:regional_indicator_y:**: Yellow Bird**\n\n:regional_indicator_o:**: Orange Bird**\n\n:regional_indicator_r:**: Red Bird**\n\n",color=0x45c4ff)
#rolemenu.set_thumbnail(url='https://cdn.discordapp.com/attachments/522777063376158760/569239529148645376/bird.gif')

#welcome_menu=discord.Embed(title="React to get a role",description="<:welcome_bird:588032757133869097> : The <@&584461501109108738> role, you will be pinged in <#526882555174191125> every time someone joins.",color=0x45c4ff)
#welcome_menu.set_thumbnail(url='https://cdn.discordapp.com/emojis/588032757133869097.png')


@bot.event
async def on_ready():
 print("working...")
 print(round(bot.latency*1000,3))
 await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name="to Steve's voice"))
 #announcement_channel=bot.get_channel(414064220196306968)
 #await announcement_channel.send(embed=temp_announcement)
 #rm=bot.get_channel(558333807548432395)
 #await rm.send(embed=welcome_menu)
 #rulech=bot.get_channel(414268041787080708)
 #msg=await rulech.fetch_message(564349454254211073)
 #await msg.edit(embed=embed)




taskobj=bot.loop.create_task(mod_admin_shuffle())

bot.run(token)
