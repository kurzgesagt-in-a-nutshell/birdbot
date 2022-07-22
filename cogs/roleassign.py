from importlib.util import LazyLoader
import logging

import json

import discord
from discord.ext import commands
from utils.helper import devs_only

class Roleassign(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger('Roleassign')
        self.bot = bot
        with open("roleassigns.json", "r") as f:
            self.roles = json.loads(f.read())
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Roleassign')
        guild = discord.utils.get(self.bot.guilds, id=414027124836532234)
        for messageid in self.roles:
            channel = discord.utils.get(guild.channels, id=self.roles[messageid]["channel"])
            message = await channel.fetch_message(messageid)
            view = discord.ui.View(timeout=None)
            for button in self.roles[messageid]["buttons"]:
                view.add_item(Button(label=button["label"], role=button["role"], roles=self.roles[messageid]["roles"]))
            await message.edit(view=view)
               

    @devs_only()
    @commands.command(hidden=True)
    async def register_messages(self, ctx, confirm):
        """Command description""" 

        if confirm != "yes":
            return

        roles = {"colours": {"embed": {'thumbnail': {'url': 'https://cdn.discordapp.com/attachments/522777063376158760/569239529148645376/bird.gif'}, 'color': 4572415, 'description': '**:Violet Bird**\n**Pink Bird**\n**Blue Bird**\n**Green Bird**\n**Yellow Bird**\n**Orange Bird**\n**Red Bird**', 'title': 'Press the button to get the role'},
         "list": [{"label": "Violet", "role": 558336866621980673}, {"label": "Pink", "role": 557944766869012510}, {"label": "Blue", "role": 557944673205747733}, {"label": "Green", "role": 557944598857646080}, {"label": "Yellow", "role": 557944535288643616}, {"label": "Orange", "role": 557944471736680474}, {"label": "Red", "role": 557944390753058816}],
          "addroles": False},
          "welcome": {"embed": {'thumbnail': {'url': 'https://cdn.discordapp.com/emojis/588032757133869097.png'}, 'color': 4572415, 'description': 'The <&584461501109108738> role, you will be pinged in <#526882555174191125> every time someone joins.', 'title': 'Press the button to get the role'},
          "list": [{"label": "Welcome Bird", "role": 584461501109108738}],
          "addroles": True},
          "languages": {"embed": {'thumbnail': {'url': 'https://cdn.discordapp.com/emojis/672323362797780992.png'}, 'color': 4572415, 'description': 'English\n\nDeutsch\n\nEspañol', 'title': 'React to get notified when a video goes live'},
          "list": [{"label": "English", "role": 901136119863844864}, {"label": "Deutsch", "role": 642097150158962688}, {"label": "Español", "role": 677171902397284363}],
          "addroles": True}
        }
        rolemessages = {}

        for message in roles:
            items = roles[message]["list"]
            if roles[message]["addroles"] == False:
                otherroles = [x["role"] for x in items]
            else:
                otherroles = []
            view = discord.ui.View(timeout=None)
            for button in items:
                view.add_item(Button(label=button["label"], role=button["role"], roles=otherroles))
            embed = discord.Embed.from_dict(roles[message]["embed"])
            messageobj = await ctx.send(embed=embed, view=view)
            rolemessages[messageobj.id] = {"buttons": items}
            rolemessages[messageobj.id].update({"roles": otherroles})
            rolemessages[messageobj.id].update({"channel": ctx.channel.id})

        with open("roleassigns.json", "w") as f:
            f.write(json.dumps(rolemessages, indent=4))

    
class Button(discord.ui.Button):
    def __init__(self, label, role, roles):
        super().__init__(label=label)
        self.role = role
        self.roles = roles
    async def callback(self, interaction):
        role = discord.utils.get(interaction.guild.roles, id=self.role)
        if role in interaction.user.roles:
            status = "removed"
            await interaction.user.remove_roles(role)
        else:
            status = "assigned"
            roleids = [r.id for r in interaction.user.roles]
            for id in roleids:
                if id in self.roles:
                    await interaction.user.remove_roles(discord.utils.get(interaction.guild.roles, id=id))
            await interaction.user.add_roles(role)

        await interaction.response.send_message(f"{role.name} {status}", ephemeral=True)        
        

async def setup(bot):
    await bot.add_cog(Roleassign(bot))
