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
        if check_message(message, get_word_list(message)):
            print("filtered " + message.content)
            await message.delete()
            await message.channel.send("Be nice, Don't say bad things " + message.author.name, delete_after=10)

    @commands.Cog.listener()
    async def on_message_edit(self, oldMessage, newMessage):
        if check_message(newMessage, get_word_list(newMessage)):
            print("filtered " + newMessage.content)
            await newMessage.delete()
            await newMessage.channel.send("Be nice, Don't say bad things " + newMessage.author.name, delete_after=10)

    @commands.Cog.listener()
    async def on_message_update(self, oldMessage, newMessage):
        if check_message(newMessage, get_word_list(newMessage)):
            print("filtered " + newMessage.content)
            await newMessage.delete()
            await newMessage.channel.send("Be nice, Don't say bad things " + newMessage.author.name, delete_after=10)


def get_word_list(message):
    if message.channel == 546315063745839115:
        return humanities_list
    else:
        return general_list


def update_swearlist():
    with open('swearfilters/humanitiesfilter.txt') as f:
        humanities_list = f.read().splitlines()
    with open('swearfilters/generalfilter.txt') as f:
        general_list = f.read().splitlines()


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
                                                  message_clean[i.start() + 2: i.end() - 2])
    indexes = re.finditer("(\*.*\*)", message_clean)
    if indexes:
        for i in indexes:
            message_clean = message_clean.replace(message_clean[i.start():i.end()],
                                                  message_clean[i.start() + 1: i.end() - 1])

    message_clean = message_clean.replace("(:.*:)", "*")
    if profanity.contains_profanity(message_clean):
        # detected swear word
        print("profanity")
        return True
        # await message.add_reaction("👎")
    elif profanity.contains_profanity(str(message_clean).replace(" ", "")):
        print("profanity")
        return True
    else:
        print(message_clean)
        for regex in regexlist:
            if re.search(regex, message_clean):
                print(re.findall(regex, message_clean))
                print("regex")
                return True


with open('swearfilters/humanitiesfilter.txt') as f:
    humanities_list = f.read().splitlines()
with open('swearfilters/generalfilter.txt') as f:
    general_list = f.read().splitlines()


def setup(bot):
    bot.add_cog(Filter(bot))


def generate_regex(words):
    joining_chars = '[ \*_\-\+\.]*'
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
        ' ': ' _\-\+\.\*'
    }
    regexlist = []
    for word in words:
        regex_parts = []

        for c in word:
            regex_parts.append("[" + replacement.get(c) + "]")
        regex = r'\b(' + joining_chars.join(regex_parts) + ')'
        # print(regex)
        regexlist.append(regex)

    return regexlist
