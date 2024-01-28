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

import argparse
import asyncio
import logging
import os

import dotenv

from app.birdbot import BirdBot, setup

parser = argparse.ArgumentParser()
parser.add_argument("-b", "--beta", help="Run the beta instance of the bot", action="store_true")
parser.add_argument("-a", "--alpha", help="Run the alpha instance of the bot", action="store_true")


async def main() -> None:
    with setup():
        logger = logging.getLogger("Startbot")
        dotenv.load_dotenv()
        args = parser.parse_args()
        bot = BirdBot.from_parseargs(args)
        if args.beta:
            token: str | None = os.environ.get("BETA_BOT_TOKEN")
        elif args.alpha:
            token: str | None = os.environ.get("ALPHA_BOT_TOKEN")
        else:
            token: str | None = os.environ.get("MAIN_BOT_TOKEN")
        async with bot:
            if token:
                await bot.start(token, reconnect=True)
            else:
                logger.critical("No token found")
                exit(-1)


if __name__ == "__main__":
    asyncio.run(main())
