# Copyright (C) 2024, Kurzgesagt Community Devs
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

"""
Weather cog – provides current weather information for any city worldwide.
Uses the free Open-Meteo API (no API key required).

"""

from __future__ import annotations

import logging

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from app.birdbot import BirdBot


WEATHER_CODES: dict[int, str] = {
    0: "Clear sky ☀️",
    1: "Mainly clear 🌤️",
    2: "Partly cloudy ⛅",
    3: "Overcast ☁️",
    45: "Fog 🌫️",
    48: "Depositing rime fog 🌫️",
    51: "Light drizzle 🌧️",
    53: "Moderate drizzle 🌧️",
    55: "Dense drizzle 🌧️",
    61: "Slight rain 🌦️",
    63: "Moderate rain 🌧️",
    65: "Heavy rain 🌧️",
    71: "Slight snow fall ❄️",
    73: "Moderate snow fall ❄️",
    75: "Heavy snow fall ❄️",
    95: "Thunderstorm ⚡",
}

DIRECTIONS = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
]


class Weather(commands.Cog):
    """Cog that provides current weather information for any city."""

    def __init__(self, bot: BirdBot) -> None:
        self.bot = bot
        self.logger = logging.getLogger("Weather")

    @app_commands.command(name="weather", description="Get current weather for a city")
    @app_commands.describe(city="The city name (e.g. London, Tokyo, Karachi)")
    async def weather(self, interaction: discord.Interaction, city: str) -> None:
        """Fetch and display current weather for the given city."""
        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: Geocode city name → coordinates
                geo_url = (
                    "https://geocoding-api.open-meteo.com/v1/search"
                    f"?name={discord.utils.escape_markdown(city)}&count=1&language=en"
                )
                async with session.get(geo_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            "❌ Could not reach geocoding service. Try again later.",
                            ephemeral=True,
                        )
                        return
                    geo_data = await resp.json()

                if not geo_data.get("results"):
                    await interaction.followup.send(
                        f"❌ Could not find city **{discord.utils.escape_markdown(city)}**. "
                        "Check spelling or try a larger city.",
                        ephemeral=True,
                    )
                    return

                location = geo_data["results"][0]
                lat = location["latitude"]
                lon = location["longitude"]
                city_name = location.get("name", city)
                country = location.get("country", "")
                admin1 = location.get("admin1", "")

                location_str = city_name
                if admin1 and admin1 != city_name:
                    location_str += f", {admin1}"
                if country:
                    location_str += f", {country}"

                # Step 2: Fetch current weather
                weather_url = (
                    "https://api.open-meteo.com/v1/forecast"
                    f"?latitude={lat}&longitude={lon}"
                    "&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
                    "weather_code,wind_speed_10m,wind_direction_10m,precipitation"
                    "&timezone=auto"
                )
                async with session.get(weather_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            "❌ Could not fetch weather data. Try again later.",
                            ephemeral=True,
                        )
                        return
                    weather_data = await resp.json()

                current = weather_data["current"]

                # Weather description
                weather_desc = WEATHER_CODES.get(current["weather_code"], "Unknown condition")

                # Wind direction
                wind_dir_index = int((current["wind_direction_10m"] + 11.25) // 22.5) % 16
                wind_dir = DIRECTIONS[wind_dir_index]

                embed = discord.Embed(
                    title=f"🌤️ Weather in {location_str}",
                    description=weather_desc,
                    color=0x1E90FF,
                    timestamp=discord.utils.utcnow(),
                )
                embed.add_field(
                    name="🌡️ Temperature", value=f"{current['temperature_2m']}°C", inline=True
                )
                embed.add_field(
                    name="🤔 Feels Like", value=f"{current['apparent_temperature']}°C", inline=True
                )
                embed.add_field(
                    name="💧 Humidity", value=f"{current['relative_humidity_2m']}%", inline=True
                )
                embed.add_field(
                    name="💨 Wind",
                    value=f"{current['wind_speed_10m']} km/h {wind_dir}",
                    inline=True,
                )
                embed.add_field(
                    name="🌧️ Precipitation", value=f"{current['precipitation']} mm", inline=True
                )

                embed.set_footer(text="Powered by Open-Meteo • Data updates hourly")

                await interaction.followup.send(embed=embed)

        except aiohttp.ClientError as e:
            self.logger.error("Weather command network error: %s", e)
            await interaction.followup.send(
                "❌ Network error while fetching weather. Try again later.", ephemeral=True
            )
        except Exception as e:
            self.logger.exception("Unexpected error in weather command")
            await interaction.followup.send(
                "❌ An unexpected error occurred. Try again later.", ephemeral=True
            )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.logger.info("Weather cog loaded")


async def setup(bot: BirdBot) -> None:
    """Load the Weather cog."""
    await bot.add_cog(Weather(bot))
