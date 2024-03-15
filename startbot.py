"""
This is the entrypoint used to start the bot.
It provides command-line arguments to specify which instance of the bot to run (beta, alpha, or main).
It loads the necessary environment variables from a .env file and starts the bot with the specified token.

Usage:
    python3 startbot.py [-b] [-a]

Options:
    -b, --beta      Run the beta instance of the bot
    -a, --alpha     Run the alpha instance of the bot
"""

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
