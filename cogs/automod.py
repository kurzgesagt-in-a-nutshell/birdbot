import json
import typing
import datetime
import logging
import re
import asyncio
import demoji
from better_profanity import profanity

import discord
from discord import http
from discord.ext import commands

from utils.helper import (
    create_automod_embed,
    mod_and_above,
)

from difflib import SequenceMatcher


def add_to_general(word):
    with open("swearfilters/generalfilter.txt", "a") as f:
        f.write(word)


class Filter(commands.Cog):
    def __init__(self, bot):
        self.logger = logging.getLogger("Automod")
        self.bot = bot

        config_file = open("config.json", "r")
        self.config_json = json.loads(config_file.read())
        config_file.close()

        self.logging_channel_id = self.config_json["logging"]["logging_channel"]
        self.logging_channel = None

        self.humanities_list = []
        self.general_list = []
        self.white_list = []
        self.message_history_list = {}
        self.message_history_lock = asyncio.Lock()
        with open("swearfilters/humanitiesfilter.txt") as f:
            self.humanities_list = f.read().splitlines()
        with open("swearfilters/generalfilter.txt") as f:
            self.general_list = f.read().splitlines()
        with open("swearfilters/whitelist.txt") as f:
            self.white_list = f.read().splitlines()

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Automod")
        self.logging_channel = await self.bot.fetch_channel(self.logging_channel_id)

    @commands.command()
    @mod_and_above()
    async def showlist(self, ctx, channel: typing.Optional[discord.TextChannel] = None):
        """Display blacklist for particular channel. Passing no channel will show the whitelist
        Usage: showlist <#channel>"""
        if channel is None:
            await ctx.send(
                "These are the words which are whitelisted",
                file=discord.File("swearfilters/whitelist.txt"),
            )
        elif channel.id == 546315063745839115:
            await ctx.send(
                "These are the words which are blacklisted only in <#546315063745839115>",
                file=discord.File("swearfilters/humanitiesfilter.txt"),
            )
        else:
            await ctx.send(
                "These are the words which are blacklisted everywhere",
                file=discord.File("swearfilters/generalfilter.txt"),
            )

    @commands.command(aliases=["remove_word"])
    @mod_and_above()
    async def removeword(self, ctx, channel: discord.TextChannel, *, word):
        """Removes a word from the filter list
        Usage: remove_word <#channel> word"""

        to_open = (
            "swearfilters/humanitiesfilter.txt"
            if channel.id == 546315063745839115
            else "swearfilters/generalfilter.txt"
        )
        words = open(to_open, "r").read().splitlines()
        if word not in words:
            await ctx.send(f"{word} doesn't appear to be blacklisted")
            return
        words.remove(word)
        with open(to_open, "w") as f:
            for word in words:
                f.write(word + "\n")
        self.update_lists()
        await ctx.message.add_reaction("<:kgsYes:580164400691019826>")

    @commands.command(aliases=["blacklistword"])
    @mod_and_above()
    async def blacklist_word(self, ctx, channel: discord.TextChannel, *, words):
        """Add a word to the blacklist. Pass humanities as the channel to add word to humanities blacklist.
        Usage: blacklistword <#channel> word_here"""
        words = words.split(" ")
        if channel.id == 546315063745839115:  # humanities
            for word in words:
                self.add_to_humanities(word)
        else:
            for word in words:
                add_to_general(word)
        self.update_lists()
        await ctx.message.add_reaction("<:kgsYes:580164400691019826>")

    @commands.command(aliases=["whitelistword"])
    @mod_and_above()
    async def whitelist_word(self, ctx, *, words):
        """Add a word to the whitelist.
        Usage: whitelist_worwhitelist_word <#channel> word_here"""
        words = words.split(" ")
        for word in words:
            self.add_to_whitelist(word)
        self.update_lists()
        await ctx.message.add_reaction("<:kgsYes:580164400691019826>")

    @commands.command()
    @mod_and_above()
    async def filter_check(self, ctx, channel: discord.TextChannel, *, words):
        if channel.id == 546315063745839115:
            await ctx.send(await self.check_message(words, self.humanities_list))
        else:
            await ctx.send(await self.check_message(words, self.humanities_list))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick == after.nick:
            return
        await self.check_member(after)

    @commands.Cog.listener()
    async def on_message(self, message):
        # if message.channel.id == 414179142020366336:
        if message.channel.id == 414452106129571842:
            return
        if message.channel.category.id == 940955259273113702:  # language survey
            return

        self.logging_channel = await self.bot.fetch_channel(self.logging_channel_id)
        if not isinstance(message.channel, discord.DMChannel):
            await self.moderate(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.channel.id == 414452106129571842:
            return
        if after.channel.category.id == 940955259273113702:  # language survey
            return
        if before.content == after.content:
            return
        if not isinstance(after.channel, discord.DMChannel):
            await self.moderate(after)

    async def check_member(self, member):
        # TODO make more modular after policy review

        if member.nick is None:
            if not re.match(r"[a-zA-Z0-9~!@#$%^&*()_+`;':\",./<>?]{3,}", member.name):
                await member.edit(nick="Unpingable Nickname")
                return

        if not re.match(r"[a-zA-Z0-9~!@#$%^&*()_+`;':\",./<>?]{3,}", member.nick):
            await member.edit(nick="Unpingable Username")
            return

        if any(s in member.nick for s in ("nazi","hitler", "führer", "fuhrer")):
            await member.edit(nick=None)
            return

        if any(s in member.name for s in ("nazi","hitler", "führer", "fuhrer")):
            await member.edit(nick="Parrot")
            return

    async def moderate(self, message):

        if self.is_member_excluded(message.author):
            return

        wordlist = self.get_word_list(message)
        event = await self.check_message(message, wordlist)

        if event[0]:
            if event[1] == "profanity":
                await self.execute_action_on_message(
                    message,
                    {
                        "ping": "Be nice, Don't say bad things",
                        "delete_after": 30,
                        "delete_message": "",
                        "log": "profanity",
                    },
                )
            if event[1] == "emoji":
                await self.execute_action_on_message(
                    message,
                    {
                        "ping": "Please do not spam emojis",
                        "delete_after": 15,
                        "delete_message": "",
                        "log": "Emoji Spam",
                    },
                )
            if event[1] == "text":
                await self.execute_action_on_message(
                    message,
                    {
                        "ping": "Please do not spam",
                        "delete_after": 15,
                        "delete_message": event[2],
                        "log": "Text Spam",
                        "mute": 60,
                    },
                )
            if event[1] == "bypass":
                await self.execute_action_on_message(
                    message,
                    {
                        "ping": "Please do not post gifs/videos in general",
                        "delete_after": 15,
                        "delete_message": "",
                        "log": "Media in #general",
                    },
                )

    async def execute_action_on_message(self, message, actions):
        # TODO: make embeds more consistent once mod policy is set
        if "ping" in actions:
            if "delete_after" in actions:
                await message.channel.send(
                    f"{actions.get('ping') } {message.author.mention}",
                    delete_after=actions.get("delete_after"),
                )
            else:
                await message.channel.send(
                    f"{actions.get('ping')} {message.author.mention}",
                    delete_after=30,
                )

        if "mute" in actions:
            time = (
                datetime.datetime.utcnow() + datetime.timedelta(seconds=actions["mute"])
            ).isoformat()
            route = http.Route(
                "PATCH", f"/guilds/414027124836532234/members/{message.author.id}"
            )
            await self.bot.http.request(
                route, json={"communication_disabled_until": time}, reason="spam"
            )

            try:
                await message.author.send(
                    f"You have been muted for 30 minutes.\nGiven reason: Spam\n"
                )

            except discord.Forbidden:
                pass

        if "delete_message" in actions:
            if isinstance(actions["delete_message"], int):
                async with self.message_history_lock:
                    for i in range(4):
                        await self.message_history_list[actions["delete_message"]][
                            i
                        ].delete()
                    self.message_history_list[
                        actions["delete_message"]
                    ] = self.message_history_list[actions["delete_message"]][3:]
            else:
                await message.delete()

        # if "warn" in actions:
        # logic for warn here

        # if "message" in actions:
        # logic for messaging the user

        if "log" in actions:
            embed = create_automod_embed(
                message=message, automod_type=actions.get("log")
            )
            await self.logging_channel.send(embed=embed)

    def get_word_list(self, message):
        if message.channel == 546315063745839115:
            return self.humanities_list
        else:
            return self.general_list

    def is_member_excluded(self, author):
        rolelist = [
            414092550031278091,  # mod
            414029841101225985,  # admin
            414954904382210049,  # offical
            414155501518061578,  # robobird
            240254129333731328,  # stealth
        ]
        if author.bot:
            return True
        if any(x in [role.id for role in author.roles] for x in rolelist):
            return True
        return False

    def update_lists(self):
        with open("swearfilters/humanitiesfilter.txt", "r") as f:
            self.humanities_list = f.read().splitlines()
        with open("swearfilters/generalfilter.txt", "r") as f:
            self.general_list = f.read().splitlines()
        with open("swearfilters/whitelist.txt", "r") as f:
            self.white_list = f.read().splitlines()

    def add_to_humanities(self, word):
        with open("swearfilters/humanitiesfilter.txt", "a") as f:
            f.write(word)

    def add_to_whitelist(self, word):
        with open("swearfilters/whitelist.txt", "a") as f:
            f.write(word+"\n")

    async def check_message(self, message, word_list):

        # check for profanity
        def check_profanity(word_list, message):
            profanity.load_censor_words(word_list)
            regex_list = self.generate_regex(word_list)
            # stores all words that are aparently profanity
            offending_list = []
            toReturn = False
            # filter out bold and italics but keep *
            message_clean = message.content
            indexes = re.finditer("(\*\*.*\*\*)", message.content)
            if indexes:
                tracker = 0
                for i in indexes:
                    message_clean = message_clean.replace(
                        message_clean[i.start() - tracker : i.end() - tracker],
                        message_clean[i.start() + 2 - tracker : i.end() - 2 - tracker],
                    )
                    tracker = tracker + 4
            indexes = re.finditer(r"(\*.*\*)", message_clean)
            if indexes:
                tracker = 0
                for i in indexes:
                    message_clean = message_clean.replace(
                        message_clean[i.start() - tracker : i.end() - tracker],
                        message_clean[i.start() + 1 - tracker : i.end() - 1 - tracker],
                    )
                    tracker = tracker + 2
            # Chagnes letter emojis to normal ascii ones
            message_clean = self.convert_regional(message_clean)
            # find all question marks in message
            indexes = [x.start() for x in re.finditer(r"\?", message_clean)]
            # get rid of all other non ascii charcters
            message_clean = demoji.replace(message_clean, "*")
            message_clean = (
                str(message_clean)
                .encode("ascii", "replace")
                .decode()
                .lower()
                .replace("?", "*")
            )
            # put back question marks
            message_clean = list(message_clean)
            for i in indexes:
                message_clean[i] = "?"
            message_clean = "".join(message_clean)
            # sub out discord emojis
            message_clean = re.sub(r"(<[A-z]*:[^\s]+:[0-9]*>)", "*", message_clean)
            if profanity.contains_profanity(message_clean):
                return True
            elif profanity.contains_profanity(str(message_clean).replace(" ", "")):
                return True
            else:
                for regex in regex_list:
                    if re.search(regex, message_clean):
                        found_items = re.findall(regex[:-3] + "[A-z]*)", message_clean)
                        for e in found_items:
                            offending_list.append(e)
                        toReturn = True
            if toReturn:
                if self.exception_list_check(offending_list):
                    return toReturn

            return False

        # check for emoji spam
        def check_emoji_spam(message):
            if message.channel.id == 526882555174191125:  # new-members
                return False

            if (
                len(
                    re.findall(
                        r"((<a?)?:\w+:(\d{18}>)?)",
                        re.sub(
                            r"(>[^\s]*<)+",
                            "> <",
                            str(message.content).encode("ascii", "ignore").decode(),
                        ),
                    )
                )
                + len(demoji.findall_list(message.content))
                > 5
            ):
                return True
            return False

        # check for text spam
        def check_text_spam(self, message):
            if message.channel.id == 526882555174191125:  # new-members
                return False

            # if the user has past messages
            if message.author.id in self.message_history_list:
                adv = 0
                count = len(self.message_history_list[message.author.id])
                # atleast 3 prior messages
                if count > 3:
                    for m in self.message_history_list[message.author.id]:
                        adv = (
                            adv
                            + SequenceMatcher(None, m.content, message.content).ratio()
                        )
                    # if the passed x message are similar with a 75% threshold
                    if adv / count > 0.60:
                        return message.author.id
            if message.channel.id in self.message_history_list:
                match_count = 0
                # atleast 3 prior messages
                if len(self.message_history_list[message.channel.id]) > 5:
                    for m in self.message_history_list[message.channel.id]:
                        if (
                            SequenceMatcher(None, m.content, message.content).ratio()
                            > 0.75
                        ):
                            match_count = match_count + 1
                        if match_count > 3:
                            return message.channel.id

        # check for mass ping
        def check_ping_spam(message):
            if len(message.mentions) > 5:
                return ["True", "ping"]

        # check for gif bypass
        def check_gif_bypass(message):

            filetypes = ["mp4", "gif", "webm", "gifv"]

            # general, bot-testing and humanities
            if not message.channel.id in (
                414027124836532236,
                414179142020366336,
                546315063745839115,
            ):
                return

            if message.embeds:
                for e in message.embeds:
                    if any(s in e.type for s in filetypes):
                        return True
                    elif e.thumbnail:
                        if any(s in e.thumbnail.url for s in filetypes):
                            return True
                    elif e.image:
                        if any(s in e.image.url for s in filetypes):
                            return True
            return False

        # run checks
        if check_profanity(word_list, message):
            return [True, "profanity"]
        if check_emoji_spam(message):
            return [True, "emoji"]
        if check_gif_bypass(message):
            return [True, "bypass"]
        if check_ping_spam(message):
            return [True, "ping"]

        # this one goes last due to lock
        async with self.message_history_lock:

            # if getting past this point we write to message history and pop if to many messages
            # spam = check_text_spam(self, message)
            # if spam:
            #     return [True, "text", spam]

            message.channel.id
            if message.author.id in self.message_history_list:
                found = False
                for n in self.message_history_list[message.author.id]:
                    if message.id == n.id:
                        found = True
                        # update existing message with edits if any
                        self.message_history_list[message.author.id][
                            self.message_history_list[message.author.id].index(n)
                        ] = message
                if not found:
                    self.message_history_list[message.author.id].append(message)
            else:
                self.message_history_list[message.author.id] = [message]

            if message.channel.id in self.message_history_list:
                found = False
                for n in self.message_history_list[message.channel.id]:
                    if message.id == n.id:
                        found = True
                        # update existing message with edits if any
                        self.message_history_list[message.channel.id][
                            self.message_history_list[message.channel.id].index(n)
                        ] = message
                if not found:
                    self.message_history_list[message.channel.id].append(message)
            else:
                self.message_history_list[message.channel.id] = [message]

            if len(self.message_history_list[message.author.id]) > 5:
                self.message_history_list[message.author.id].pop(0)

            if len(self.message_history_list[message.channel.id]) > 10:
                self.message_history_list[message.channel.id].pop(0)

        return [False, "none"]

    def exception_list_check(self, offending_list):
        for bad_word in offending_list:
            if not bad_word in self.white_list:
                return True

        return False

    def convert_regional(self, word):
        replacement = {
            "🇦": "a",
            "🇧": "b",
            "🇨": "c",
            "🇩": "d",
            "🇪": "e",
            "🇫": "f",
            "🇬": "g",
            "🇭": "h",
            "🇮": "i",
            "🇯": "j",
            "🇰": "k",
            "🇱": "l",
            "🇲": "m",
            "🇳": "n",
            "🇴": "o",
            "🇵": "p",
            "🇶": "q",
            "🇷": "r",
            "🇸": "s",
            "🇹": "t",
            "🇺": "u",
            "🇻": "v",
            "🇼": "w",
            "🇽": "x",
            "🇾": "y",
            "🇿": "z",
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
            "a": r"4a\@\#",
            "b": r"b\*",
            "c": r"c¢\*",
            "d": r"d\*",
            "e": r"e\*",
            "f": r"f\*",
            "g": r"g\*",
            "h": r"h\*",
            "i": r"!1il\*",
            "j": r"!j\*",
            "k": r"k\*",
            "l": r"!1il\*",
            "m": r"m\*",
            "n": r"n\*",
            "o": r"o\*",
            "p": r"pq\*",
            "q": r"qp\*",
            "r": r"r\*",
            "s": r"s$\*",
            "t": r"t\+\*",
            "u": r"uv\*",
            "v": r"vu\*",
            "w": r"w\*",
            "x": r"x\*",
            "y": r"y\*",
            "z": r"z\*",
            " ": r" _\-\+\.*",
        }
        regexlist = []
        for word in words:
            regex_parts = []
            for c in word:
                regex_parts.append(f"[{replacement.get(c)}]")
            regex = r"\b(" + joining_chars.join(regex_parts) + r")\b"
            regexlist.append(regex)
        return regexlist


def setup(bot):
    bot.add_cog(Filter(bot))
