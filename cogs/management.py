import discord
from discord.ext import commands


class Management(commands.Cog, name='Management'):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print('loaded management')

    @commands.guild_only()
    @commands.command()
    async def emojis(self, ctx):
        """Shows a list of emojis"""
        desc=""
        embed = discord.Embed(title = f"{ctx.guild}'s Emojis")
        emojis = ctx.guild.emojis
        length=0
        for i in range(len(emojis)):
            length+=len(str(emojis[i]))+len(str(emojis[i].name))+2
            if length < 1000:
                desc += f"{emojis[i].name}: {str(emojis[i])}\n"
            else:
                embed.add_field(name="​", value = desc)
                desc=""
                length=0
        embed.add_field(name="​", value = desc)
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command()
    async def roles(self, ctx):
        """Prints a list roles"""
        rolelist = []
        for i in ctx.guild.roles:
            rolelist.append(f'{i.name} : {i.color}')
        embed = discord.Embed(title = f"{ctx.guild}'s Roles", description = ("\n".join(rolelist)))
        await ctx.send(embed = embed)

    @commands.has_any_role('Kurz Temp Access', 'Administrator', 'Moderator')
    @commands.command()
    async def send(self, ctx, channel, *, string):
        """Sends a message."""
        msgchannel = discord.utils.get(self.bot.get_guild(414027124836532234).channels, name=channel)
        if "@everyone" or "@here" not in string:
            await msgchannel.send(string)

    @commands.command(aliases = ["bi"])
    async def boostinfo(self, ctx, guild: discord.Guild = None):
        """Shows the boosting status of the server"""
        if guild is None:
            guild = ctx.guild
        
        embed = discord.Embed(colour = 0x36393f, title = f"{guild}'s Nitro Boost stats")
        embed.add_field(name = "Boosts", value = guild.premium_subscription_count, inline = True)
        embed.add_field(name = "Tier", value = guild.premium_tier, inline = True)
        if guild.splash is None:
            splash = "N/A"
        else:
            splash = str(guild.splash_url)
            embed.set_image(url = splash)
        if guild.premium_tier == 0:
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/emojis/682980900480614426.png?v=1")
        elif guild.premium_tier == 1:
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/emojis/682980953001689098.png?v=1")
        elif guild.premium_tier == 2:
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/emojis/682980985385648156.png?v=1")
        elif guild.premium_tier == 3:
            embed.set_thumbnail(
                url="https://cdn.discordapp.com/emojis/682981007422390322.png?v=1")

        if guild.premium_tier != 3:
            tier_3 = 30
            tier_2 = 15
            tier_1 = 2
            if guild.premium_tier == 0:
                embed.add_field(name="Boosts until __Tier 1__ <:boost1:700827342032863333>",
                                value=tier_1 - guild.premium_subscription_count, inline=True)
            elif guild.premium_tier == 1:
                embed.add_field(name="Boosts until __Tier 2__ <:boost2:700827341911228466>",
                                value=tier_2 - guild.premium_subscription_count, inline=True)
            elif guild.premium_tier == 2:
                embed.add_field(name="Boosts until __Tier 3__ <:boost3:700827341940850688>",
                                value=tier_3 - guild.premium_subscription_count, inline=True)
        
        if guild.splash is None:
            splash = "N/A"

        else:
            splash = f"[Link]({guild.splash_url})"

        if guild.banner is None:
            banner = "N/A"

        else:
            banner = f"[Link]({guild.banner_url})"

        try:
            invite = await guild.vanity_invite()
            vanity = f"[Link]({invite})"
        except discord.HTTPException:
            vanity = "N/A"
        except Exception:
            vanity = "N/A"

        embed.add_field(name = "Splash URL", value = splash, inline = True)
        embed.add_field(name = "Banner URL", value = banner, inline = True)
        embed.add_field(name = "Vanity URL", value = vanity, inline = True)

        if guild.features:

            features = []

            for feature in guild.features:
                if feature[1]:
                    features.append(feature.title())

            embed.add_field(name = f"Features [{len(features)}]", value = ", ".join(features).replace("_", " "), inline = True)
        
        else:
            embed.add_field(name = f"Features [0]", value = "This guild has no features", inline = True)

        number = 0

        if guild.premium_subscribers:

            boosters = []
            for booster in guild.premium_subscribers:
                number += 1
                boosters.append(f"`{number}.` {booster} since `{booster.premium_since.strftime('%a, %#d %B %Y, %I:%M %p UTC')}`")

            embed.add_field(name = f"Boosters [{len(boosters)}]", value = "\n".join(boosters), inline = False)

        else:
            embed.add_field(name = f"Boosters [0]", value = "This guild has no boosters", inline = False)

        await ctx.send(embed = embed)
def setup(bot):
    bot.add_cog(Management(bot))
