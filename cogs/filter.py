import logging
import re

from profanity_filter import ProfanityFilter

from better_profanity import profanity
from discord.ext import commands


class Filter(commands.Cog):

    def __init__(self, bot):
        self.logger = logging.getLogger('Filter')
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Filter')

    @commands.Cog.listener()
    async def on_message(self, message):
        if check_message(message, slur_list):
            print("filtered " + message.content)

    @commands.Cog.listener()
    async def on_message_edit(self, oldMessage, newMessage):
        if check_message(newMessage, slur_list):
            print("filtered " + newMessage.content)

    @commands.Cog.listener()
    async def on_message_update(self, oldMessage, newMessage):
        if check_message(newMessage, slur_list):
            print("filtered " + newMessage.content)


def update_swearlist():
    with open('swearfilters/humanitiesfilter.txt') as f:
        restricted_list = f.read().splitlines()
    with open('swearfilters/generalfilter.txt') as f:
        slur_list = f.read().splitlines()


def add_badword(word):
    with open('swearfilters/humanitiesfilter.txt', 'a') as f:
        f.write(word)
    with open('swearfilters/generalfilter.txt', 'a') as f:
        f.write(word)


def check_message(message, wordlist):
    profanity.load_censor_words(wordlist)
    regexlist = generate_regex(wordlist)
    # get rid of all non ascii charcters
    message_clean = str(message.content).encode("ascii", "ignore").decode()
    # filter out bold and italics but keep *
    indexes = re.finditer("(\*\*.*\*\*)", message_clean)
    if indexes:
        for i in indexes:
            message_clean = message_clean.replace(message_clean[i.start():i.end()],
                                                  message_clean[i.start() + 2 : i.end() - 2])
    indexes = re.finditer("(\*.*\*)", message_clean)
    if indexes:
        for i in indexes:
            message_clean = message_clean.replace(message_clean[i.start():i.end()],
                                                  message_clean[i.start() + 1 : i.end() - 1])

    message_clean = message_clean.replace("(:.*:)", "*")
    print(message_clean)

    if profanity.contains_profanity(message_clean):
        # detected swear word
        print("profanity")
        return True
        # await message.add_reaction("👎")
    elif profanity.contains_profanity(str(message_clean).replace(" ", "")):
        print("profanity")
        return True
    else:
        for regex in regexlist:
            if re.search(regex, message_clean):
                print(re.findall(regex, message_clean))
                print("regex")
                return True


with open('swearfilters/humanitiesfilter.txt') as f:
    restricted_list = f.read().splitlines()
with open('swearfilters/generalfilter.txt') as f:
    slur_list = f.read().splitlines()


def setup(bot):
    bot.add_cog(Filter(bot))

    with open('swearfilters/humanitiesfilter.txt') as f:
        restricted_list = f.read().splitlines()
    with open('swearfilters/generalfilter.txt') as f:
        slur_list = f.read().splitlines()


def generate_regex(words):
    joining_chars = '[_\-\+\.]*'
    replacement = {
        'a': 'a\@\#',
        'b': 'b\*',
        'c': 'c\*',
        'd': 'd\*',
        'e': 'e\*',
        'f': 'f\*',
        'g': 'g\*',
        'h': 'h\*',
        'i': '1il\*',
        'j': 'j\*',
        'k': 'k\*',
        'l': '1i1l\*',
        'm': 'm\*',
        'n': 'ｎ\*',
        'o': 'o\*',
        'p': 'pq\*',
        'q': 'qp\*',
        'r': 'r\*',
        's': 's$\*',
        't': 't\+\*',
        'u': 'uv\*',
        'v': 'vu\*',
        'w': 'w\*',
        'x': 'x\*',
        'y': 'y\*',
        'z': 'z\*',
        ' ': ' _\-\+\.*'
    }
    regexlist = []
    for word in words:
        regex_parts = []

        for c in word:
            regex_parts.append("[" + replacement.get(c) + "]")
        regex = '\b(' + joining_chars.join(regex_parts) + ')'

        # print(regex)
        regexlist.append(regex)

    return regexlist
