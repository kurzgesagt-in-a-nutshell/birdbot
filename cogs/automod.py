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


    @commands.command()
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
        await ctx.message.add_reaction('<:kgsYes:580164400691019826>')

    @commands.command()
    @helper_and_above()
    async def whitelistword(self, ctx, *, words):
        words = words.split(" ")
        for word in words:
            await self.add_to_whitelist()
        self.update_lists()
        await ctx.message.add_reaction('<:kgsYes:580164400691019826>')

    @commands.command()
    @helper_and_above()
    async def filtercheck(self, ctx, channel, *, words):
        if channel == "humanities":
            await ctx.send(self.check_message_for_profanity(words,self.humanities_list))
        else:
            await ctx.send(self.check_message_for_profanity(words, self.humanities_list))


    @commands.Cog.listener()
    async def on_message(self, message):
        await self.moderate(message)

    @commands.Cog.listener()
    async def on_message_edit(self, oldMessage, newMessage):
        await self.moderate(newMessage)

    @commands.Cog.listener()
    async def on_message_update(self, oldMessage, newMessage):
        await self.moderate(newMessage)

    async def moderate(self, message):
        event = False
        if str(message.channel.type) == "private":
            wordlist = self.general_list
            event = self.check_message_for_profanity(message.content, wordlist)
            if event[0]:
                if event[1] == "profanity":
                    print("filtered " + message.content)
                    #await message.delete()
                    await message.channel.send("Be nice, Don't say bad things " + message.author.mention,
                                               delete_after=30)
                    await message.add_reaction('<:kgsYes:580164400691019826>')
                if event[1] == "emoji":
                    print("Emoji Spam detected" + message.content)
                    #await message.delete()
                    await message.channel.send("Please do not spam emojis " + message.author.mention, delete_after=20)
                    await message.add_reaction('<:kgsYes:580164400691019826>')
                if event[1] == "text":
                    print("text spam detected" + message.content)
                    #await message.delete()
                    await message.channel.send("Please do not spam " + message.author.mention, delete_after=20)
                    await message.add_reaction('<:kgsYes:580164400691019826>')

        elif not self.isExcluded(message.author):
            wordlist = self.get_word_list(message)
            event = self.check_message_for_profanity(message.content, wordlist)
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
        with open('swearfilters/whitelist.txt', 'a') as f:
            self.white_list = f.read().splitlines()


    def add_to_general(self, word):
        with open('swearfilters/generalfilter.txt', 'a') as f:
            f.write(word)


    def add_to_humanities(self, word):
        with open('swearfilters/humanitiesfilter.txt', 'a') as f:
            f.write(word)


    def add_to_whitelist(self, word):
        with open('swearfilters/filter.txt', 'a') as f:
            f.write(word)

    def check_message_for_profanity(self, message_content, word_list):
        profanity.load_censor_words(word_list)
        regex_list = self.generate_regex(word_list)
        # stores all words that are aparently profanity
        offending_list = []
        toReturn = [False, None]
        # filter out bold and italics but keep *
        message_clean = message_content
        indexes = re.finditer('(\*\*.*\*\*)', message_content)
        if indexes:
            tracker = 0
            for i in indexes:
                message_clean = message_clean.replace(message_clean[i.start() - tracker:i.end() - tracker],
                                                      message_clean[i.start() + 2 - tracker: i.end() - 2 - tracker])
                tracker = tracker+4
        indexes = re.finditer(r'(\*.*\*)', message_clean)
        if indexes:
            tracker = 0
            for i in indexes:
                message_clean = message_clean.replace(message_clean[i.start() - tracker:i.end() - tracker],
                                                      message_clean[i.start() + 1 - - tracker: i.end() - 1 - tracker])
                tracker = tracker + 2

        # Chagnes letter emojis to normal ascii ones
        message_clean = self.convert_regional(message_clean)
        # find all question marks in message
        indexes = [x.start() for x in re.finditer(r'\?', message_clean)]
        # get rid of all other non ascii charcters
        message_clean = demoji.replace(message_clean, '*')
        message_clean = str(message_clean).encode("ascii", "replace").decode().lower().replace("?", "*")
        # put back question marks
        message_clean = list(message_clean)
        for i in indexes:
            message_clean[i] = "?"
        message_clean = "".join(message_clean)
        # sub out discord emojis
        message_clean = re.sub(r'(<[A-z]*:[^\s]+:[0-9]*>)', '*', message_clean)
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
            if self.exception_list_check(offending_list):
                return toReturn

        # check for emoji spam
        if len(re.findall(r'(<[A-z]*:[^\s]+:[0-9]*>)', re.sub('(>[^/s]*<)+', '> <', str(message_content)
                .encode("ascii", "ignore").decode()))) + len(demoji.findall_list(message_content)) > 5:
            return [True, "emoji"]
        return [False, None]


    def check_message_for_emoji_spam(self, message):
        if len(re.findall(r'(<:[^\s]+:[0-9]*>)',
                          re.sub(r'(>[^/s]*<)+', '> <', str(message.content).encode("ascii", "ignore")
                                  .decode()))) + len(demoji.findall_list(message.content)) > 5:
            return True
        return False

    def exception_list_check(self, offending_list):
        for bad_word in offending_list:
            if bad_word in self.white_list:
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
        joining_chars = r'[ _\-\+\.*!@#$%^&():\'"]*'
        replacement = {
            'a': r'a\@\#',
            'b': r'b\*',
            'c': r'c\*',
            'd': r'd\*',
            'e': r'e\*',
            'f': r'f\*',
            'g': r'g\*',
            'h': r'h\*',
            'i': r'1il\*',
            'j': r'j\*',
            'k': r'k\*',
            'l': r'1i1l\*',
            'm': r'm\*',
            'n': r'n\*',
            'o': r'o\*',
            'p': r'pq\*',
            'q': r'qp\*',
            'r': r'r\*',
            's': r's$\*',
            't': r't\+\*',
            'u': r'uv\*',
            'v': r'vu\*',
            'w': r'w\*',
            'x': r'x\*',
            'y': r'y\*',
            'z': r'z\*',
            ' ': r' _\-\+\.*'
        }
        regexlist = []
        for word in words:
            regex_parts = []

            for c in word:
                regex_parts.append("[" + replacement.get(c) + "]")
            regex = r'\b(' + joining_chars.join(regex_parts) + ')'
            regexlist.append(regex)

        return regexlist


def setup(bot):
    bot.add_cog(Filter(bot))
