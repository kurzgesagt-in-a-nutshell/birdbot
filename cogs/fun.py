import re
import requests
from typing import Optional
import json

import discord
from discord.ext import commands

class Fun(commands.Cog, name='Fun'):
    def __init__(self, bot):
        self.bot = bot    
    
    @commands.Cog.listener()
    async def on_ready(self):
        print('loaded fun')

    @commands.command()
    async def clap(self, ctx, *, clap):
        """Replaces spaces with :clap:"""
        claps = ":clap: " + re.sub(' +', ' ', clap).replace(" ", " :clap: ") + " :clap:"
        await ctx.send(claps)

    @commands.command()
    async def weather(self, ctx, *, city, units: Optional[str] = 'C'):
        """Shows weather in a city"""
        link=' http://api.openweathermap.org/data/2.5/weather?appid=3c3fdfdd08d48ebb5a66a27e376a719f&q='
        adr = link + city
        data = requests.get(adr).json()
        countrys = json.load(open('countries.json'))
        country = countrys[data["sys"]["country"]]
        embed = discord.Embed(title = f"{city.title()}, {country}'s weather")
        val = f"{round(data['main']['temp']-273,1)} °C"
        val2 = f"{round(data['main']['feels_like']-273,1)} °C"
        if units.lower() == 'f':
            val = f"{round((data['main']['temp']-273-32)/1.8,1)} °F"
            val2 = f"{round((data['main']['feels_like']-273-32)/1.8,1)} °F"
        embed.add_field(name = "Temperature", value = val)
        embed.add_field(name = "Feels like", value = val2)
        embed.add_field(name = "Humidity", value = f"{data['main']['humidity']} %")
        embed.add_field(name = "Weather description", value = data['weather'][0]['description'])
        await ctx.send(embed = embed)

def setup(bot):
    bot.add_cog(Fun(bot))
