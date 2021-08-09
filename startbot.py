import contextlib
import os
import logging
import asyncio
import dotenv
import argparse

from kurzgesagt import BirdBot
from kurzgesagt import setup    

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
dotenv.load_dotenv()

def main():
    with setup():
        bot = BirdBot.from_parseargs(args)
        bot.load_extensions()

