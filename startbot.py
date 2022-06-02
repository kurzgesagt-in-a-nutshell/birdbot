import logging
import os
import dotenv
import argparse
import asyncio

from birdbot import BirdBot
from birdbot import setup


parser = argparse.ArgumentParser()
parser.add_argument(
    "-b", "--beta", help="Run the beta instance of the bot", action="store_true"
)
parser.add_argument(
    "-a", "--alpha", help="Run the alpha instance of the bot", action="store_true"
)

def is_member_whitelisted(ctx) -> bool:
    cmd_blacklist_db = BirdBot.db.CommandBlacklist
    cmd = cmd_blacklist_db.find_one({"command_name": ctx.command.name})
    if cmd is None:
        cmd_blacklist_db.insert_one(
            {"command_name": ctx.command.name, "blacklisted_users": []}
        )
        return True

    return ctx.author.id not in cmd["blacklisted_users"]


async def main():
    with setup():

        logger = logging.getLogger("Startbot")
        dotenv.load_dotenv()
        args = parser.parse_args()
        bot = BirdBot.from_parseargs(args)
        await bot.load_extensions(args)
        bot.add_check(is_member_whitelisted)
        if args.beta:
            token = os.environ.get("BETA_BOT_TOKEN")
        elif args.alpha:
            token = os.environ.get("ALPHA_BOT_TOKEN")
        else:
            token = os.environ.get("MAIN_BOT_TOKEN")
        bot.run(token, reconnect=True)


if __name__ == "__main__":
    asyncio.run(main())
