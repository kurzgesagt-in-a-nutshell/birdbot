import asyncio
import copy
import datetime
import io
import logging
import re
import typing

import demoji
import discord
from discord import app_commands
from discord.ext import commands

from app.utils import checks
from app.utils.config import Reference
from app.utils.helper import create_automod_embed, is_external_command, is_internal_command
from app.birdbot import BirdBot

"""

"""


class Filter(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.logger = logging.getLogger("Automod")
        self.bot = bot

        self.logging_channel_id = Reference.Channels.Logging.automod_actions
        self.logging_channel = None
        self.message_history_list = {}
        self.message_history_lock = asyncio.Lock()

        self.humanities_list: typing.List[str] = self.bot.db.filterlist.find_one({"name": "humanities"})["filter"]
        self.general_list: typing.List[str] = self.bot.db.filterlist.find_one({"name": "general"})["filter"]
        self.white_list: typing.List[str] = self.bot.db.filterlist.find_one({"name": "whitelist"})["filter"]
        self.general_list_regex = self.generate_regex(self.general_list)

        self.humanities_list_regex = self.generate_regex(self.humanities_list)

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Automod")
        self.logging_channel = await self.bot.fetch_channel(self.logging_channel_id)

    # declare command group
    filter_commands = app_commands.Group(
        name="filter",
        description="Automod filter commands",
        guild_ids=[Reference.guild],
        default_permissions=discord.permissions.Permissions(manage_messages=True),
    )

    # return the required list
    def return_list(self, listtype) -> typing.List[str]:
        if listtype == "whitelist":
            return self.white_list
        elif listtype == "general":
            return self.general_list
        elif listtype == "humanities":
            return self.humanities_list
        else:
            return []

    def return_regex(self, listtype):
        if listtype == "whitelist":
            return ""
        elif listtype == "general":
            return self.general_list_regex
        elif listtype == "humanities":
            return self.humanities_list_regex

    # Updates filter list from Mongo based on listtype
    async def updatelist(self, listtype):
        if listtype == "whitelist":
            self.white_list = self.bot.db.filterlist.find_one({"name": "whitelist"})["filter"]

        elif listtype == "general":
            self.general_list = self.bot.db.filterlist.find_one({"name": "general"})["filter"]
            self.general_list_regex = self.generate_regex(self.general_list)

        elif listtype == "humanities":
            self.humanities_list = self.bot.db.filterlist.find_one({"name": "humanities"})["filter"]
            self.humanities_list_regex = self.generate_regex(self.humanities_list)

    @filter_commands.command()
    @checks.mod_and_above()
    async def show(
        self,
        interaction: discord.Interaction,
        list_type: typing.Literal["whitelist", "general", "humanities"],
    ):
        """Show words in selected filter list

        Parameters
        ----------
        list_type: str
            Type of list
        """
        filelist = self.return_list(list_type)
        await interaction.response.send_message(
            f"These are the words which are in the {list_type}{'blacklist' if list_type != 'whitelist' else ''}",
            file=discord.File(io.BytesIO("\n".join(filelist).encode("UTF-8")), f"{list_type}.txt"),
        )

    @filter_commands.command()
    @checks.mod_and_above()
    async def add(
        self,
        interaction: discord.Interaction,
        list_type: typing.Literal["whitelist", "general", "humanities"],
        word: str,
    ):
        """Add a word in selected filter list

        Parameters
        ----------
        list_type: str
            Type of list
        word: str
            Word or regex to add in the selected list
        """
        file_list = self.return_list(list_type)
        if word in file_list:
            await interaction.response.send_message(
                f"`{word}` already exists in {list_type}{' list' if list_type != 'whitelist' else ''}.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"`{word}` added to the {list_type}{' list' if list_type != 'whitelist' else ''}."
        )

        self.bot.db.filterlist.update_one({"name": list_type}, {"$push": {"filter": word}})

        await self.updatelist(list_type)

    @filter_commands.command()
    @checks.mod_and_above()
    async def remove(
        self,
        interaction: discord.Interaction,
        list_type: typing.Literal["whitelist", "general", "humanities"],
        word: str,
    ):
        """Remove a word in selected filter list

        Parameters
        ----------
        list_type: str
            Type of list
        word: str
            Word or regex to remove in the selected list
        """
        filelist = self.return_list(list_type)
        if word not in filelist:
            await interaction.response.send_message(
                f"`{word}` doesn't exists in {list_type}{' list' if list_type != 'whitelist' else ''}.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"`{word}` removed from the {list_type}{' list' if list_type != 'whitelist' else ''}."
        )

        self.bot.db.filterlist.update_one({"name": list_type}, {"$pull": {"filter": word}})

        await self.updatelist(list_type)

    @checks.mod_and_above()
    @filter_commands.command()
    async def check(
        self,
        interaction: discord.Interaction,
        list_type: typing.Literal["general", "humanities"],
        text: str,
    ):
        """Check if a word/phrase contains profanity

        Parameters
        ----------
        list_type: str
            Type of list
        text: str
            Word or phrase to check
        """
        file_list = copy.copy(self.return_list(list_type))
        regex_list = copy.copy(self.return_regex(list_type))
        word_list = file_list
        if list_type == "humanities":
            word_list += self.general_list
            regex_list += self.general_list_regex

        profanity = self.check_profanity(word_list, regex_list, text)
        if profanity:
            await interaction.response.send_message(profanity)
        else:
            await interaction.response.send_message("No profanity.")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick == after.nick:
            return
        await self.check_member(after)

    @commands.Cog.listener()
    async def on_message(self, message):
        if isinstance(message.channel, discord.DMChannel):
            return
        if (
            message.channel.category.id == Reference.Categories.moderation
            and message.channel.id != Reference.Channels.bot_tests
        ):
            return

        if message.channel.category.id == Reference.Channels.language_tests:  # language testing
            return
        if self.is_member_excluded(message.author):
            return

        if message.content == "":
            if self.check_gif_bypass(message):
                await self.execute_action_on_message(
                    message,
                    {
                        "ping": "Please do not post gifs/videos in general",
                        "delete_after": 15,
                        "delete_message": "",
                        "log": "Media in #general",
                    },
                )
            return

        if is_internal_command(self.bot, message):
            return

        if is_external_command(message):
            return

        self.logging_channel = await self.bot.fetch_channel(self.logging_channel_id)
        if not isinstance(message.channel, discord.DMChannel):
            await self.check_message(message)
            await self.check_member(message.author)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.channel.id == Reference.Channels.bot_commands:
            return

        if self.is_member_excluded(after.author):
            return

        if (
            before.channel.category.id == Reference.Categories.moderation  # mod category
            and before.channel.id != Reference.Channels.bot_tests  # bot testing
        ):
            return
        if before.content == after.content:
            if self.check_gif_bypass(after):
                await self.execute_action_on_message(
                    after,
                    {
                        "ping": "Please do not post gifs/videos in general",
                        "delete_after": 15,
                        "delete_message": "",
                        "log": "Media in #general",
                    },
                )
            return
        if not isinstance(after.channel, discord.DMChannel):
            await self.check_message(after)

    async def check_member(self, member):
        # TODO make more modular after policy review

        if member.bot:
            return

        nickname_lock = discord.utils.get(member.guild.roles, name="Nickname Lock")
        if nickname_lock in member.roles:
            if member.name != "Kurzgesagt Fan":
                await member.edit(nick="Kurzgesagt Fan")

        if member.nick is None:
            if not re.search(r"[a-zA-Z0-9~!@#$%^&*()_+`;':\",./<>?]{3,}", member.name, re.IGNORECASE):
                await member.edit(nick="Unpingable Username")
            if any(s in member.name for s in ("nazi", "hitler", "führer", "fuhrer")):
                await member.edit(nick="Parrot")

        else:
            if not re.search(r"[a-zA-Z0-9~!@#$%^&*()_+`;':\",./<>?]{3,}", member.nick, re.IGNORECASE):
                await member.edit(nick="Unpingable Nickname")
            if any(s in member.nick for s in ("nazi", "hitler", "führer", "fuhrer")):
                await member.edit(nick=None)

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

        if "delete_message" in actions:
            if isinstance(actions["delete_message"], int):
                async with self.message_history_lock:
                    for i in range(4):
                        await self.message_history_list[actions["delete_message"]][i].delete()
                    self.message_history_list[actions["delete_message"]] = self.message_history_list[
                        actions["delete_message"]
                    ][4:]
            else:
                await message.delete()

        if "mute" in actions:
            time = datetime.timedelta(seconds=actions["mute"])
            await message.author.timeout(time, reason="spam")

            try:
                await message.author.send(f"You have been muted for 30 minutes.\nGiven reason: Spam\n")

            except discord.Forbidden:
                pass

        # if "warn" in actions:
        # logic for warn here

        # if "message" in actions:
        # logic for messaging the user

        if "log" in actions:
            embed = create_automod_embed(message=message, automod_type=actions.get("log"))
            await self.logging_channel.send(embed=embed)

    def is_member_excluded(self, author):
        rolelist = [
            Reference.Roles.moderator,  # mod
            Reference.Roles.administrator,  # admin
            Reference.Roles.kgsofficial,  # offical
            Reference.Roles.robobird,  # robobird
            Reference.Roles.stealthbot,  # stealth
        ]
        if author.bot:
            return True
        if any(x in [role.id for role in author.roles] for x in rolelist):
            return True
        return False

    def check_profanity(self, ref_word_list, regex_list, message_clean):
        # filter out bold and italics but keep *
        indexes = re.finditer("(\*\*.*?\*\*)", message_clean)
        if indexes:
            tracker = 0
            for i in indexes:
                message_clean = message_clean.replace(
                    message_clean[i.start() - tracker : i.end() - tracker],
                    message_clean[i.start() + 2 - tracker : i.end() - 2 - tracker],
                )
                tracker = tracker + 4
        indexes = re.finditer(r"(\*.*?\*)", message_clean)
        if indexes:
            tracker = 0
            for i in indexes:
                message_clean = message_clean.replace(
                    message_clean[i.start() - tracker : i.end() - tracker],
                    message_clean[i.start() + 1 - tracker : i.end() - 1 - tracker],
                )
                tracker = tracker + 2
        # Changes letter emojis to normal ascii ones
        message_clean = self.convert_regional(message_clean)
        # changes cyrllic letters into ascii ones
        message_clean = self.convert_letters(message_clean)
        # find all question marks in message
        indexes = [x.start() for x in re.finditer(r"\?", message_clean)]
        # get rid of all other non ascii characters
        message_clean = demoji.replace(message_clean, "*")
        message_clean = str(message_clean).encode("ascii", "replace").decode().lower().replace("?", "*")
        # put back question marks
        message_clean = list(message_clean)
        for i in indexes:
            message_clean[i] = "?"
        message_clean = "".join(message_clean)
        # sub out discord emojis
        message_clean = re.sub(r"(<[A-z]*:[^\s]+:[0-9]*>)", "*", message_clean)
        dirty_list = []
        for regex in regex_list:
            if re.search(regex, message_clean):
                found_items = re.findall(regex[:-3] + "[A-z]*)", message_clean)
                for e in found_items:
                    dirty_list.append(e)
        clean_list = []
        # test to see if any word is within a already existing word
        for test_word in dirty_list:
            found = False
            for to_match in dirty_list:
                if (
                    test_word[0] in to_match[0]
                    and len(test_word[0]) < len(to_match[0])
                    and test_word[1] >= to_match[1]
                    and test_word[2] < to_match[2]
                ):
                    found = True
                    break
            if not found:
                clean_list.append(test_word)
        # does the final check to see if any word is not in the whitelist
        for bad_word in clean_list:
            if not bad_word in self.white_list:
                return clean_list
        return False

    def exception_list_check(self, offending_list):
        for bad_word in offending_list:
            if not bad_word in self.white_list:
                return False
        return True

    # check for emoji spam
    def check_emoji_spam(self, message):
        if message.channel.id == Reference.Channels.new_members:  # new-members
            return False

        if (
            len(
                re.findall(
                    r"((<a?)?:\w+:(\d{18}>)?)",
                    re.sub(
                        r"(>[\s]*<)+",
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
        if message.channel.id == Reference.Channels.new_members:  # new-members
            return False

        # if the user has past messages
        if message.author.id in self.message_history_list:
            count = len(self.message_history_list[message.author.id])
            if count > 3:
                if all(m.content == message.content for m in self.message_history_list[message.author.id][0:4]):
                    return message.author.id

        if message.channel.id in self.message_history_list:
            if len(self.message_history_list[message.channel.id]) > 3:
                if all(m.content == message.content for m in self.message_history_list[message.channel.id][0:4]):
                    return message.channel.id

    # check for mass ping
    def check_ping_spam(self, message):
        if len(message.mentions) > 5:
            return ["True", "ping"]

    # check for gif bypass
    def check_gif_bypass(self, message):
        filetypes = ["mp4", "gif", "webm", "gifv"]

        if message.channel.id not in (
            Reference.Channels.general,
            Reference.Channels.bot_tests,
            Reference.Channels.humanities,
        ):
            return
        # This is too aggressive and shouldn't be necessary. Leaving it commented for now though.
        """for f in filetypes:
            if "." + f in message.content:
                return True"""

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
        if message.attachments:
            for e in message.attachments:
                if any(s in e.filename for s in filetypes):
                    return True
                elif any(s in e.url for s in filetypes):
                    return True
        return False

    async def check_message(self, message):
        word_list = copy.copy(self.return_list(message.channel.name))
        regex_list = copy.copy(self.return_regex(message.channel.name))
        if word_list is None:
            word_list = copy.copy(self.general_list)
            regex_list = copy.copy(self.general_list_regex)

        if message.channel.name == "humanities":
            word_list += self.general_list
            regex_list += self.general_list_regex

        # run checks
        is_profanity = self.check_profanity(word_list, regex_list, message.content)
        if is_profanity:
            await self.execute_action_on_message(
                message,
                {
                    "ping": "Be nice, Don't say bad things",
                    "delete_after": 30,
                    "delete_message": "",
                },
            )

            embed = create_automod_embed(message=message, automod_type="profanity")
            embed.add_field(name="Blacklisted Word", value=is_profanity[:1024], inline=False)
            file = discord.File(io.BytesIO(message.content.encode("UTF-8")), f"log.txt")
            await self.logging_channel.send(embed=embed, file=file)
            return
        if self.check_emoji_spam(message):
            await self.execute_action_on_message(
                message,
                {
                    "ping": "Please do not spam emojis",
                    "delete_after": 15,
                    "delete_message": "",
                    "log": "Emoji Spam",
                },
            )
            return
        if self.check_ping_spam(message):
            # why is nothing here
            return [True, "ping"]
        if self.check_gif_bypass(message):
            await self.execute_action_on_message(
                message,
                {
                    "ping": "Please do not post gifs/videos in general",
                    "delete_after": 15,
                    "delete_message": "",
                    "log": "Media in #general",
                },
            )
            return

        # this one goes last due to lock
        async with self.message_history_lock:

            # if getting past this point we write to message history and pop if to many messages

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

        spam = self.check_text_spam(message)
        if spam:
            await self.execute_action_on_message(
                message,
                {
                    "ping": "Please do not spam",
                    "delete_after": 15,
                    "delete_message": spam,
                    "log": "Text Spam",
                    "mute": 1800,
                },
            )

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

    def convert_letters(self, word):
        replacement = {
            "а": "a",
            "в": "b",
            "с": "c",
            "е": "e",
            "н": "h",
            "к": "k",
            "м": "m",
            "и": "n",
            "о": "o",
            "р": "p",
            "🇷": "r",
            "т": "t",
            "ш": "w",
            "х": "x",
            "у": "y",
            "“": '"',
            "”": '"',
            "’": "'",
            "⁰": "0",
            "¹": "1",
            "²": "2",
            "³": "3",
            "⁴": "4",
            "⁵": "5",
            "⁶": "6",
            "⁷": "7",
            "⁸": "8",
            "⁹": "9",
            "′": "'",
        }

        to_return = ""
        letter_list = list(word)
        for letter in letter_list:
            if replacement.get(letter.lower()) is not None:
                to_return = to_return + replacement.get(letter.lower())
            else:
                to_return = to_return + letter
        return to_return

    def generate_regex(self, words):
        joining_chars = r'[ _\-\+\.\*!@#$%^&():;\[\]\}\{\'"]*'
        replacement = {
            "a": r"4a\@\#",
            "b": r"b\*",
            "c": r"c¢\*",
            "d": r"d\*",
            "e": r"e3\*",
            "f": r"f\*",
            "g": r"g\*",
            "h": r"h\*",
            "i": r"!1il\*",
            "j": r"!j\*",
            "k": r"k\*",
            "l": r"!1il\*",
            "m": r"m\*",
            "n": r"n\*",
            "o": r"o0\*",
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


async def setup(bot: BirdBot):
    await bot.add_cog(Filter(bot))
