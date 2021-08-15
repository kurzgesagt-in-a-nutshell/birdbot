import logging
import re
import this
import contextlib
import demoji
import discord
from better_profanity import profanity
from discord import guild
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
        await moderate(message)

    @commands.Cog.listener()
    async def on_message_edit(self, oldMessage, newMessage):
        await moderate(newMessage)

    @commands.Cog.listener()
    async def on_message_update(self, oldMessage, newMessage):
        await moderate(newMessage)


async def moderate(message):
    event = False;
    # print(message.content)
    if not isExcluded(message.author):
        event = check_message_for_profanity(message, get_word_list(message))
        if event[0]:
            if event[1] == "profanity":
                print("filtered " + message.content)
                await message.delete()
                await message.channel.send("Be nice, Don't say bad things " + message.author.name, delete_after=10)
            if event[1] == "emoji":
                print("Emoji Spam detected" + message.content)
                await message.delete()
                await message.channel.send("Please do not spam emojis" + message.author.name, delete_after=20)
            if event[1] == "text":
                print("text spam detected" + message.content)
                await message.delete()
                await message.channel.send("Please do not spam" + message.author.name, delete_after=20)


def get_word_list(message):
    if message.channel == 546315063745839115:
        return this.humanitieslist
    else:
        return this.generallist


def isExcluded(author):
    rolelist = [
        # 849423379706150946,  # helper
        414092550031278091,  # mod
        414029841101225985,  # admin
        414954904382210049,  # offical
        414155501518061578,  # robobird
        240254129333731328  # stealth
    ]
    if author.bot:
        return True

    for role in author.roles:
        if role.id in rolelist:
            return True
    return False


def update_swear_list():
    with open('swearfilters/humanitiesfilter.txt') as f:
        this.humanities_list = f.read().splitlines()
    with open('swearfilters/generalfilter.txt') as f:
        this.general_list = f.read().splitlines()


def add_badword(word):
    with open('swearfilters/humanitiesfilter.txt', 'a') as f:
        f.write(word)
    with open('swearfilters/generalfilter.txt', 'a') as f:
        f.write(word)


def check_message_for_profanity(message, wordlist):
    profanity.load_censor_words(wordlist)
    regexlist = generate_regex(wordlist)
    # stores all words that are aparently profanity
    offendinglist = []
    toReturn = [False, None]
    # Chagnes letter emojis to normal ascii ones
    message_clean = convert_regional(message.content)
    # find all question marks in message
    indexes = [x.start() for x in re.finditer('\?', message_clean)]
    # get rid of all other non ascii charcters
    message_clean = str(message_clean).encode("ascii", "replace").decode().lower().replace("?", "*")
    # put back question marks
    message_clean = list(message_clean)
    for i in indexes:
        message_clean[i] = "?"
    message_clean = "".join(message_clean)
    # sub out discord emojis
    message_clean = re.sub('(<[A-z]*:[^\s]+:[0-9]*>)', '*', message_clean)
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

    if profanity.contains_profanity(message_clean):
        return [True, "profanity"]
    elif profanity.contains_profanity(str(message_clean).replace(" ", "")):
        return [True, "profanity"]
    else:
        for regex in regexlist:
            if re.search(regex, message_clean):
                founditems = (re.findall(regex[:-1] + '[A-z]*)', message_clean))
                for e in founditems:
                    offendinglist.append(e)
                toReturn = [True, "profanity"]
    if toReturn[0]:
        if exception_list_check(offendinglist):
            print("here")
            return toReturn

    # check for emoji spam
    if len(re.findall('(<[A-z]*:[^\s]+:[0-9]*>)', re.sub('(>[^/s]*<)+', '> <', str(message.content)
            .encode("ascii", "ignore").decode()))) + len(demoji.findall_list(message.content)) > 5:
        return [True, "emoji"]

    return [False, None]


def check_message_for_emoji_spam(message):
    if len(re.findall('(<:[^\s]+:[0-9]*>)', re.sub('(>[^/s]*<)+', '> <', str(message.content).encode("ascii", "ignore")
            .decode()))) + len(demoji.findall_list(message.content)) > 5:
        return True
    return False


def exception_list_check(offendinglist):
    for badword in offendinglist:
        if badword in this.exceptionlist:
            continue
        else:
            return True

    return False


def convert_regional(word):
    replacement = {
        '🇦': 'a',
        '🇧': 'b',
        '🇨': 'c',
        '🇩': 'd',
        '🇪': 'e',
        '🇫': 'f',
        '🇬': 'g',
        '🇭': 'h',
        '🇮': 'i',
        '🇯': 'j',
        '🇰': 'k',
        '🇱': 'l',
        '🇲': 'm',
        '🇳': 'n',
        '🇴': 'o',
        '🇵': 'p',
        '🇶': 'q',
        '🇷': 'r',
        '🇸': 's',
        '🇹': 't',
        '🇺': 'u',
        '🇻': 'v',
        '🇼': 'w',
        '🇽': 'x',
        '🇾': 'y',
        '🇿': 'z'
    }

    counter = 0
    toreturn = ""
    letterlist = list(word)
    for letter in letterlist:
        if replacement.get(letter) != None:
            toreturn = toreturn + replacement.get(letter)
        else:
            toreturn = toreturn + letter
        counter = counter + 1
    return toreturn


def generate_regex(words):
    joining_chars = '[ _\-\+\.\*!@#$%^&():\'"]*'
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
        'n': 'n\*',
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
        regex = r'\b(' + joining_chars.join(regex_parts) + ')'
        # print(regex)
        regexlist.append(regex)

    return regexlist


def setup(bot):
    bot.add_cog(Filter(bot))
    this.eventist = {}
    with open('swearfilters/humanitiesfilter.txt') as f:
        this.humanitieslist = f.read().splitlines()
    with open('swearfilters/generalfilter.txt') as f:
        this.generallist = f.read().splitlines()
    with open('swearfilters/exceptionfilter.txt') as f:
        this.exceptionlist = f.read().splitlines()
