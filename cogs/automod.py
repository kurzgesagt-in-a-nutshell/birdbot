import logging
import re
import demoji
from better_profanity import profanity
from discord.ext import commands

from utils.helper import mod_and_above, helper_and_above


class Filter(commands.Cog):

    def __init__(self, bot):
        self.logger = logging.getLogger('Automod')
        self.bot = bot

        self.humanities_list = []
        self.general_list = []
        self.white_list = []
        with open('swearfilters/humanitiesfilter.txt') as f:
            self.humanities_list = f.read().splitlines()
        with open('swearfilters/generalfilter.txt') as f:
            self.general_list = f.read().splitlines()
        with open('swearfilters/whitelist.txt') as f:
            self.white_list = f.read().splitlines()

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info('loaded Automod')

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.moderate(message)

    @commands.Cog.listener()
    async def on_message_edit(self, oldMessage, newMessage):
        await self.moderate(newMessage)

    @commands.Cog.listener()
    async def on_message_update(self, oldMessage, newMessage):
        await self.moderate(newMessage)

    @commands.Cog.listener()
    @helper_and_above()
    async def blacklistword(self, ctx, channel, *, words):
        words = words.split(" ")
        if channel.name == "humanities":
            for word in words:
                await self.add_to_humanities(word)
        else:
            for word in words:
                await self.add_to_general(word)
        self.update_lists()

    @commands.Cog.listener()
    @helper_and_above()
    async def whitelistword(self, ctx, *, words):
        words = words.split(" ")
        for word in words:
            await self.add_to_whitelist()
        self.update_lists()

    @commands.Cog.listener()
    @helper_and_above()
    async def test(self, ctx, channel, *, words):
        if channel.name == "humanities":
            ctx.send(self.check_message_for_emoji_spam(words))
        else:
            ctx.send(self.check_message_for_emoji_spam(words))

    async def moderate(self, message):
        event = False
        # print(message.content)
        if not self.isExcluded(message.author):
            wordlist = self.get_word_list(message)
            event = self.check_message_for_profanity(message, wordlist)
            print(event)
            if event[0]:
                if event[1] == "profanity":
                    print("filtered " + message.content)
                    await message.delete()
                    await message.channel.send("Be nice, Don't say bad things " + message.author.mention,
                                               delete_after=30)
                if event[1] == "emoji":
                    print("Emoji Spam detected" + message.content)
                    await message.delete()
                    await message.channel.send("Please do not spam emojis " + message.author.mention, delete_after=20)
                if event[1] == "text":
                    print("text spam detected" + message.content)
                    await message.delete()
                    await message.channel.send("Please do not spam " + message.author.mention, delete_after=20)

    def get_word_list(self, message):
        if message.channel == 546315063745839115:
            return self.humanities_list
        else:
            return self.general_list

    def isExcluded(self, author):
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

    def update_lists(self):
        with open('swearfilters/humanitiesfilter.txt') as f:
            self.humanities_list = f.read().splitlines()
        with open('swearfilters/generalfilter.txt') as f:
            self.general_list = f.read().splitlines()
        with open('swearfilters/filter.txt', 'a') as f:
            self.white_list = f.read().splitlines()

    def add_to_general(self, word):
        with open('swearfilters/humanitiesfilter.txt', 'a') as f:
            f.write(word)

    def add_to_humanities(self, word):
        with open('swearfilters/generalfilter.txt', 'a') as f:
            f.write(word)

    def add_to_whitelist(self, word):
        with open('swearfilters/filter.txt', 'a') as f:
            f.write(word)

    def check_message_for_profanity(self, message, wordlist):
        print("Orginal: " + message.content)
        profanity.load_censor_words(wordlist)
        regex_list = self.generate_regex(wordlist)
        # stores all words that are aparently profanity
        offending_list = []
        toReturn = [False, None]
        # Chagnes letter emojis to normal ascii ones
        message_clean = self.convert_regional(message.content)
        print("Regional:" + message_clean)
        # find all question marks in message
        indexes = [x.start() for x in re.finditer('\?', message_clean)]
        # get rid of all other non ascii charcters
        message_clean = str(message_clean).encode("ascii", "replace").decode().lower().replace("?", "*")
        print("ASCII:" + message_clean)
        # put back question marks
        message_clean = list(message_clean)
        for i in indexes:
            message_clean[i] = "?"
        message_clean = "".join(message_clean)
        print("Cleaned: " + message_clean)
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
            for regex in regex_list:
                if re.search(regex, message_clean):
                    found_items = (re.findall(regex[:-1] + '[A-z]*)', message_clean))
                    for e in found_items:
                        offending_list.append(e)
                    toReturn = [True, "profanity"]
        if toReturn[0]:
            if self.exception_list_check(self, offending_list):
                return toReturn

        # check for emoji spam
        if len(re.findall('(<[A-z]*:[^\s]+:[0-9]*>)', re.sub('(>[^/s]*<)+', '> <', str(message.content)
                .encode("ascii", "ignore").decode()))) + len(demoji.findall_list(message.content)) > 5:
            return [True, "emoji"]

        return [False, None]

    def check_message_for_emoji_spam(self, message):
        if len(re.findall('(<:[^\s]+:[0-9]*>)',
                          re.sub('(>[^/s]*<)+', '> <', str(message.content).encode("ascii", "ignore")
                                  .decode()))) + len(demoji.findall_list(message.content)) > 5:
            return True
        return False

    def exception_list_check(self, offending_list):
        for bad_word in offending_list:
            if bad_word in self.whitelist:
                continue
            else:
                return True

        return False

    def convert_regional(self, word):
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
        to_return = ""
        letter_list = list(word)
        for letter in letter_list:
            if replacement.get(letter) is not None:
                to_return = to_return + replacement.get(letter)
            else:
                to_return = to_return + letter
            counter = counter + 1
        return to_return


    def generate_regex(self, words):
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
