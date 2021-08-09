import logging
import os
import dotenv
import argparse

from birdbot import BirdBot
from birdbot import setup

parser = argparse.ArgumentParser()
parser.add_argument("-b",
                    "--beta",
                    help="Run the beta instance of the bot",
                    action="store_true")
parser.add_argument("-a",
                    "--alpha",
                    help="Run the alpha instance of the bot",
                    action="store_true")


def main():
    with setup():
        logger = logging.getLogger("Startbot")
        dotenv.load_dotenv()
        args = parser.parse_args()
        bot = BirdBot.from_parseargs(args)
        bot.get_database()
        bot.load_extensions()
        if args.beta:
            token = os.environ.get("BETA_BOT_TOKEN")
        elif args.alpha:
            token = os.environ.get("ALPHA_BOT_TOKEN")
        else:
            token = os.environ.get("MAIN_BOT_TOKEN")
        bot.run(token, reconnect=True)

if __name__ == '__main__':
    main()
