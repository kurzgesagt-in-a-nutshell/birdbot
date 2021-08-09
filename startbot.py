import logging
import os
import dotenv
import argparse

from startbot import BirdBot
from startbot import setup

parser = argparse.ArgumentParser()
parser.add_argument("-b",
                    "--beta",
                    help="Run the beta instance of the bot",
                    action="store_true")
parser.add_argument("-a",
                    "--alpha",
                    help="Run the alpha instance of the bot",
                    action="store_true")
args = parser.parse_args()

logger = logging.getLogger("Startbot")
logger.info(args)

dotenv.load_dotenv()

def main():
    with setup():
        bot = BirdBot.from_parseargs(args)
        bot.load_extensions()
        if args.beta:
            token = os.environ.get("BETA_BOT_TOKEN")
        if args.alpah:
            token = os.environ.get("ALPHA_BOT_TOKEN")
        else:
            token = os.environ.get("MAIN_BOT_TOKEN")
        bot.run(token, reconnect=True)

if __name__ == '__main__':
    main()
