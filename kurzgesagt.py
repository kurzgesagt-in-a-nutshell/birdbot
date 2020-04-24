import logging
logging.basicConfig(level=logging.INFO)
import discord,asyncio,time,typing,inspect
from itertools import cycle
from discord.ext import commands
prefix = 'k!'
bot = commands.Bot(command_prefix=prefix)
token = 'NDcxNzA1NzE4OTU3ODAxNDgz.XN7cLw.ntikeK86SgIq58QCw4_apMPfI30'
<<<<<<< HEAD
token2='NjM5NTA4NTE3NTM0OTU3NTk5.Xn4Wgg.BLKvrblu-10X-GSG7rQIyqoAM0I'
=======
token2='NjM5NTA4NTE3NTM0OTU3NTk5.Xb7V5Q.O3WHaQhujIDljrqEe2aiDbAex2I'
>>>>>>> f8205c6341d78643db977372189bd083316cbb41




@bot.event
async def on_message(message):
    ks = bot.get_guild(414027124836532234)
    fm=ks.get_channel(677771290186219554)
    if message.channel ==  fm:
        await message.add_reaction("<:bird_yes:580164400691019826>")
        await message.add_reaction("<:bird_no:610542174127259688>")

@bot.command()
@commands.is_owner()
@commands.has_any_role(414092550031278091,414029841101225985,414954904382210049)
async def ban(ctx,members: commands.Greedy[discord.Member],delete_messages: typing.Optional[int]=0,*,reason: str):
    for member in members:
        await member.ban(delete_message_days=delete_messages,reason=reason)
        await member.ban(delete_message_days=delete_messages,reason=reason)
    await ctx.send("**Banned!** {} for {}".format(member,reason))
        
@ban.error
async def ban_error(ctx,error):
    if isinstance(error,commands.MissingAnyRole):
        await ctx.send('You are not authorized to perform this action')

@bot.command()
async def filter(ctx,msg: int,*,role: str):
    ks = bot.get_guild(414027124836532234)
    giveaway_channel=bot.get_channel(414064220196306968)
    threshold_role= discord.utils.get(ks.roles,name=role)
    giveaway_message=giveaway_channel.fetch_message(msg)
    giveaway_reaction = giveaway_message.reactions
    users=await giveaway_message.reactions.users().flatten()
    i=0
    for i in users:
        if threshold_role in i.roles:
            pass
        else:
            await giveaway_message.reactions.remove(i)
    
@bot.command()
@commands.has_any_role(414092550031278091,414029841101225985,414954904382210049,483132576291094528)
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


linklist=['http://kurzgesagt.org/','https://www.youtube.com/user/Kurzgesagt','https://www.youtube.com/user/KurzgesagtDE','https://www.patreon.com/Kurzgesagt','https://www.reddit.com/r/kurzgesagt/','https://twitter.com/Kurz_Gesagt','https://www.instagram.com/kurz_gesagt/','https://www.facebook.com/Kurzgesagt/','https://www.behance.net/kurzgesagt','https://soundcloud.com/epicmountain','https://open.spotify.com/artist/7meq0SFt3BxWzjbt5EVBbT?si=y0-yrHExQJKtCLc1WHaQ8A','https://discord.gg/cB7ycdv']


@bot.command(name='eval', pass_context=True)
@commands.is_owner()
async def eval_(ctx, *, command):
    res = eval(command)
    if inspect.isawaitable(res):
        await ctx.send(await res)
        await ctx.message.add_reaction('\U00002705')
    else:
        await ctx.send(res)
        
@eval_.error
async def eval_error(ctx,error):
    if isinstance(error,commands.CheckFailure):
        await ctx.send("Y u tryna run an owner only command?")


            
    
# async def my_background_task():
    # await bot.wait_until_ready()
    # counter = 0
    # ks = bot.get_guild(414027124836532234)
    
    # banner_list=[]
    # for i in range(1,16):
             
         # with open("/home/pi/Pictures/kimages/{}.png".format(i), "rb") as image:
            # f = image.read()
            # b = bytearray(f)
            # banner_list.append(b)
    # print(len(banner_list))
   
    # while not bot.is_closed():
        # if counter>15:
            # counter=0
        # await ks.edit(banner=banner_list[counter])
        # counter = counter + 1
        
        # print('Changed Banner to ',counter)
        # await asyncio.sleep(1800) 
        
@bot.event
<<<<<<< HEAD
async def on_ready(): 
 print("working")
 ks = bot.get_guild(414027124836532234)
 jk=bot.get_guild(482936367043837972)

=======
async def on_ready():
 ks = bot.get_guild(414027124836532234)
 jk=bot.get_guild(482936367043837972)
 await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name="to Steve's voice"))
 
>>>>>>> f8205c6341d78643db977372189bd083316cbb41
 
 
 
  
     
 #announcement_channel=bot.get_channel(414064220196306968)
 #msg= await announcement_channel.fetch_message(623541883825553450)
 #await msg.edit(content='<:bird_thonk:606149684922155018>',embed=temp_announcement2)
 #rm=bot.get_channel(558333807548432395)
 #await rm.send(embed=welcome_menu)
 #rulech=bot.get_channel(414268041787080708)
 #msg=await rulech.fetch_message(564349454254211073)
 #await msg.edit(embed=embed)



 # i=0
 # for i in ks.features:
    # print(i)
    # if i == 'BANNER':
        # bot.loop.create_task(my_background_task())
        # print('Shuffling banners')
        
    # else:
        # print('Banner shuffle disabled')
bot.run(token2)
