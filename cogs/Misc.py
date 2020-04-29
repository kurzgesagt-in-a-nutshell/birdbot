import re
import requests
import json

import discord
from discord.ext import commands

class Misc(commands.Cog, name='Fun'):
    def __init__(self, bot):
        self.bot = bot    

    def is_botcommands(ctx):
        return ctx.message.channel.id == 414452106129571842 or ctx.message.channel.id == 414179142020366336

    @commands.Cog.listener()
    async def on_ready(self):
        print('loaded Misc')

    @commands.check(is_botcommands)
    @commands.command()
    async def clap(self, ctx, *, clap):
        """Replaces spaces with :clap:"""
        claps = ":clap: " + re.sub(' +', ' ', clap).replace(" ", " :clap: ") + " :clap:"
        await ctx.send(claps)

    @commands.check(is_botcommands)
    @commands.command()
    async def weather(self, ctx, *, city):
        """Shows weather in a city"""
        link = 'http://api.openweathermap.org/data/2.5/weather?appid=3c3fdfdd08d48ebb5a66a27e376a719f&q='
        adr = link + city.replace(" ", "%20")
        data = requests.get(adr).json()
        countrys = json.load(open('countries.json'))
        country = countrys[data["sys"]["country"]]
        embed = discord.Embed(title = f"{data['name']}, {country}'s weather")
        if data['name'] == country:
            embed = discord.Embed(title = f"{country}'s weather")
        valc = f"{round(data['main']['temp']-273,1)} °C"
        valc2 = f"{round(data['main']['feels_like']-273,1)} °C"
        valf = f"{round((data['main']['temp']-273-32)/1.8,1)} °F"
        valf2 = f"{round((data['main']['feels_like']-273-32)/1.8,1)} °F"
        embed.add_field(name = "Temperature", value = valc + "\n" + valf)
        embed.add_field(name = "Feels like", value = valc2 + "\n" + valf2)
        embed.add_field(name = "Humidity", value = f"{data['main']['humidity']} %")
        embed.add_field(name = "Weather description", value = data['weather'][0]['description'])
        await ctx.send(embed = embed)

def setup(bot):
    bot.add_cog(Misc(bot))
