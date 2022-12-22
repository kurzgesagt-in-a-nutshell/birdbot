import enum, typing
import discord

from birdbot import BirdBot

INFRACTION_DB = BirdBot.db.Infraction

class InfractionKind(enum.Enum):
    WARN    = 0
    MUTE    = 1
    KICK    = 2
    BAN     = 3


class Infraction: 
    """
    Represents an infraction in the kurzgesagt server. Supports warns, mutes,
    kicks and bans
    """

    def __init__(self, kind: InfractionKind, data: typing.Dict):

        self._kind = kind
        self._author_id = data.pop('author_id', None)
        self._author_name = data.pop('author_name', None)
        self._datetime = data.pop('datetime', None)
        self._reason = data.pop('reason', None)
        self._level = data.pop('infraction_level', None)
        self._duration = data.pop('duration', None)

        # extra info such as detailed infractions are stored here
        self._extra = data

    @classmethod
    def new(
        cls, 
        kind:InfractionKind, 
        author:discord.User, 
        level:int, 
        reason:str, 
        duration:int=None
    ):
        """Creates a new infraction instance with the provided details"""

        data = {
            "author_id": author.id, 
            "author_name": author.name, 
            "infraction_level": level,
            "datetime": discord.utils.utcnow(),
            "reason": reason
        }

        if duration is not None:
            data.update({"duration": duration})

        return cls(kind, data)

    @property
    def level(self) -> typing.Union(int, str):
        """
        A property that returns the integer level of the infraction or the
        string 'legacy' if there is no level.
        """
        
        return self._level if self._level is not None else "legacy"

    def info_str(self, id:int):
        """
        Returns basic information of the infraction as a string

        The infraction's index must be passed into the method to provide an id
        """
        duration = '' if self._duration is None else f'Duration: {self._duration}\n'
        level = 'Legacy' if self._level is None else self._level

        return f"Author: {self._author_name} ({self._author_id})\n \
            Reason: {self._reason}\n \
            {duration} \
            Date: {self._date.replace(microsecond=0)}\n \
            Infraction Level: {level}\n \
            {self._kind.name.title()} ID: {id}"

    def detailed_info_embed(self, user:discord.User):
        """
        Returns detailed information on the infraction as an embed
        """

        embed = discord.Embed(
            title=f"Detailed infraction for {user.name} ({user.id}) ",
            description=f"**Infraction Type:** {self._kind.name.title()}",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(name="Author", value=f"<@{self._author_id}>", inline=True)
        embed.add_field(name="Reason", value=self._reason, inline=True)
        embed.add_field(name="Infraction Level", value=self._level, inline=True)

        if self._duration is not None:
            embed.add_field(name="Duration", value=self._duration, inline=True)

        embed.add_field(
            name="Time Issued", 
            value=f"<t:{int(self._datetime.timestamp())}>",
            inline=False
        )

        for extra in self._extra:
            embed.add_field(name=extra, value=self._extra[extra])

        return embed

    def detail(self, title:str, description):
        """
        Appends extra details to the infraction. This also allows for editing of
        contents such as the reason though I dont really want to recommend this
        method.
        """
        
        self._extra[title] = description
    
    def to_dict(self):
        """
        Serialize this instance into a dict for storage

        Always serialize the default info: author_id, author_name, datetime,
        reason, and infraction_level.

        Always append any extra info left over in the original data.
        If a duration value is present, include it into the data.
        """

        data = {
            "author_id": self._author_id,
            "author_name": self._author_name,
            "datetime": self._datetime,
            "reason": self._reason,
            "infraction_level": self._level
        }

        data.update(self._extra)

        if self._duration is not None:
            data.update({"duration": self._duration})

        return data


class InfractionList:
    """
    Represents a list of infractions for a user
    """

    def __init__(self, user: discord.User, data={}) -> None:
        
        self._user = user

        self._user_id = data.pop('user_id', user.id)
        self._user_name = data.pop('user_name', user.name)
        self._last_updated = data.pop('last_updated', discord.utils.utcnow())
        self._banned_patreon = data.pop('banned_patreon', False)
        self._final_warn = data.pop('final_warn', False)

        self._warns = [Infraction(InfractionKind.WARN, warn_data) for warn_data in data.pop('warn', [])]
        self._mutes = [Infraction(InfractionKind.MUTE, mute_data) for mute_data in data.pop('mute', [])]
        self._kicks = [Infraction(InfractionKind.KICK, kick_data) for kick_data in data.pop('kick', [])]
        self._bans = [Infraction(InfractionKind.BAN, ban_data) for ban_data in data.pop('ban', [])]

    @classmethod
    def from_user(cls, user:discord.User):
        """
        This searches the mongo db for an entry of a user. If no entry is found,
        none is returned and due to the behavior of the class, info is filled
        out accordingly.

        The user is linked to this instance and it can be updated to the 
        database whenever.
        """
        
        infractions = INFRACTION_DB.find_one({"user_id": user.id})

        return cls(user, infractions)

    def __kind_to_list(self, kind:InfractionKind) -> typing.List[Infraction]:
        """
        Returns the list of infractions corresponding to the given kind.

        This is a helper method and should be private.
        """

        if kind==InfractionKind.WARN:
            return self._warns
        elif kind==InfractionKind.MUTE:
            return self._mutes
        elif kind==InfractionKind.KICK:
            return self._kicks
        elif kind==InfractionKind.BAN:
            return self._bans

    def summary(self) -> str:
        """
        Returns a summary of the users infractions. This is the blurb of text
        shown on a user's infraction embed which contains the total infraction
        count, if the user is on final warning or not, and the quick summary of
        the layout of infraction levels.
        """

        final_warn = '' if self._final_warn is not True else 'USER IS ON FINAL WARNING\n'

        # count infraction levels
        # legacies are handled by the infraction.level property
        inflevels = {}
        inf_sum = 0

        for kind in InfractionKind:
            infrs = self.__kind_to_list(kind)
            for infraction in infrs:
                if infraction.level not in inflevels:
                    inflevels[infraction.level] = 0
                
                inflevels[infraction.level] += 1
                inf_sum += 1
        
        dectoroman = {
            "legacy": "Legacy",
            1: "I",
            2: "II",
            3: "III",
            4: "IV",
            5: "V",
        }

        valuelist = []
        for key in sorted(inflevels):
            valuelist.append(f"{inflevels[key]}x{dectoroman[key]}")

        return f"Total Infractions: {inf_sum}\n{final_warn}{', '.join(valuelist)}"

    def new_infraction(
        self,
        kind: InfractionKind, 
        level: int, 
        author: discord.User, 
        reason:str, 
        duration=None,
        final=False
    ):
        """
        Creates a new infraction locally inside the list.

        This does not update the database. A separate call to self.update() must
        be done to save changes.
        """
        
        infr = Infraction.new(kind, author, level, reason, duration)

        self.__kind_to_list(kind).append(infr)

        if final: self._final = True

    def detail_infraction(
        self, 
        kind: InfractionKind, 
        id: int, 
        title:str, 
        description: str
    ) -> bool:

        """
        Allows the editing of extra info on the infraction.

        Returns the success status as a bool in case an out of range index is
        provided.
        """
        try:
            self.__kind_to_list(kind)[id].detail(title, description)
        
        except IndexError:
            return False
        
        else: return True

    def delete_infraction(self, kind: InfractionKind, id: int) -> bool:
        
        """
        Deletes an infraction from the list.
        
        Returns the success status as a bool in case an out of range index is
        provided
        """

        try:
            del self.__kind_to_list(kind)[id]
        
        except IndexError:
            return False
        
        else: return True

    def get_infractions_of_kind(
        self, 
        kind:InfractionKind
    ) -> discord.Embed:
        """
        Returns a discord.Embed with a list and information of infractions of
        the given kind
        """

        infractions = self.__kind_to_list(kind)
        infractions_info = [v.info_str(i) for i, v in enumerate(infractions)]

        embed = discord.Embed(
            title="Infractions",
            description=" ",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow(),
        )

        embed.add_field(name=self._user_id, value=f"```\n{self.summary()}\n```")
        embed.add_field(name=kind.name.title(), value="\n\n".join(infractions_info))

        return embed

    def get_detailed_infraction(
        self, 
        kind: InfractionKind, id:int
    ) -> typing.Optional[discord.Embed]:
        """
        Returns a discord.Embed with information about the requested infraction.
        
        If no infraction of the kind and id is found, None is returned.
        """
        
        try:
            return self.__kind_to_list(kind)[id].detailed_info_embed(self._user)
        
        except IndexError:
            return None

    def to_dict(self):
        """
        Serialize the data into a dict for storage
        """

        data = {
            "user_id": self._user_id,
            "user_name": self._user_name,
            "last_updated": self._last_updated,
            "banned_patron": self._banned_patreon,
            "final_warn": self._final_warn,
            "warn": [inf.to_dict for inf in self._warns],
            "mute": [inf.to_dict for inf in self._mutes],
            "kick": [inf.to_dict for inf in self._kicks],
            "ban": [inf.to_dict for inf in self._bans]
        }

        return data

    def update(self):

        """
        syncs local updates to the database
        
        convert the data stored in the class into a dict
        """

        self._last_updated = discord.utils.utcnow()
        data = self.to_dict()

        INFRACTION_DB.update_one({"user_id": self._user_id}, {"$set": data})