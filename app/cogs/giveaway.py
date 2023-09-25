import logging
import typing
from datetime import timedelta, timezone

import discord
import numpy as np
from discord import app_commands
from discord.ext import commands, tasks

from app.utils import checks
from app.utils.config import GiveawayBias, Reference
from app.utils.helper import calc_time
from app.birdbot import BirdBot


class Giveaway(commands.Cog):
    def __init__(self, bot: BirdBot):
        self.logger = logging.getLogger("Giveaway")
        self.bot = bot
        self.active_giveaways = {}
        self.giveaway_db = self.bot.db.Giveaways

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info("loaded Giveaway")

    def cog_load(self) -> None:
        for giveaway in self.giveaway_db.find({"giveaway_over": False, "giveaway_cancelled": False}):
            giveaway["end_time"] = giveaway["end_time"].replace(tzinfo=timezone.utc)
            self.active_giveaways[giveaway["message_id"]] = giveaway

        self.giveaway_task.start()

    def cog_unload(self):
        self.giveaway_task.cancel()

    giveaway_commands = app_commands.Group(
        name="giveaway",
        description="Giveaway commands",
        guild_only=True,
        guild_ids=[Reference.guild],
        default_permissions=discord.permissions.Permissions(manage_messages=True),
    )

    async def choose_winner(self, giveaway):
        """does the giveaway logic"""
        message = False
        channel = self.bot._get_channel(giveaway["channel_id"])
        try:
            message = await channel.fetch_message(giveaway["message_id"])
        except discord.NotFound:
            pass

        if message:
            if message.author != self.bot.user:
                if giveaway["message_id"] in self.active_giveaways:
                    del self.active_giveaways[giveaway["message_id"]]
                return

            users = []
            self.logger.debug("Fetching reactions from users")
            for reaction in message.reactions:
                if reaction.emoji == "🎉":
                    userids = [user.id async for user in reaction.users() if user.id != self.bot._user().id]
                    users = []
                    for userid in userids:
                        try:
                            member = self.bot.get_user(userid)
                            users.append(member)
                        except discord.errors.NotFound:
                            pass

            self.logger.debug("Fetched users")

            if users != []:
                self.logger.debug("Calculating weights")
                weights = []
                for user in users:
                    bias = GiveawayBias.default
                    roles = [role.id for role in user.roles]
                    for role in GiveawayBias.roles:
                        if role["id"] in roles:
                            bias = role["bias"]
                            break
                    weights.append(bias)

                total = sum(weights)
                probabilities = [w / total for w in weights]
                prob = np.array(probabilities)

                if giveaway["rigged"] == False:
                    prob = None

                size = giveaway["winners_no"]
                if len(users) < size:
                    size = len(users)

                self.logger.debug("Choosing winner(s)")
                choice = np.random.choice(users, size=size, replace=False, p=prob)
                winners = []
                winnerids = ", ".join([str(i.id) for i in choice])
                self.logger.debug(f"Fetched winner(s): {winnerids}")
                for winner in choice:
                    await message.reply(f"{winner.mention} won **{giveaway['prize']}**!")
                    winners.append(f"> {winner.mention}")
                winners = "\n".join(winners)

            else:
                winners = "> Nobody participated :("
                winnerids = ""

            self.logger.debug("Sending new embed")

            time = discord.utils.utcnow() + timedelta(seconds=giveaway["end_time"])  # type: ignore

            embed = discord.Embed(
                title="Giveaway ended",
                timestamp=time,  # type: ignore
                colour=discord.Colour.red(),
            )

            embed.set_footer(text="Giveaway Ended")

            riggedinfo = ""
            if giveaway["rigged"]:
                riggedinfo = (
                    " [rigged](https://discord.com/channels/414027124836532234/414452106129571842/714496884844134401)"
                )

            description = f"**{giveaway['prize']}**\n{riggedinfo}\n"

            description += f'> **Winners: {giveaway["winners_no"]}**\n'
            description += winners + "\n"
            description += f'> **{"Hosted" if giveaway["sponsor"] == giveaway["host"] else "Sponsored"} by**\n> <@{giveaway["sponsor"]}>'

            embed.description = description

            await message.edit(embed=embed)

        else:
            self.logger.debug("Message not found")
            self.logger.debug("Deleting giveaway")
            del self.active_giveaways[giveaway["message_id"]]
            self.giveaway_db.update_one(giveaway, {"$set": {"giveaway_cancelled": True}})
            return

        if giveaway["message_id"] in self.active_giveaways:
            self.logger.debug("Deleting giveaway")
            del self.active_giveaways[giveaway["message_id"]]
            self.giveaway_db.update_one(
                giveaway,
                {"$set": {"giveaway_over": True, "winners": winnerids}},
            )
        else:
            self.logger.debug("Appending old winners and updating giveaway")
            winnerids += f", old: {giveaway['winners']}"
            self.giveaway_db.update_one(giveaway, {"$set": {"winners": winnerids}})

    @tasks.loop()
    async def giveaway_task(self):
        templist = list(self.active_giveaways)
        firstgiveaway = {}

        self.logger.debug("Checking for giveaways")
        self.logger.debug(f"{len(templist)} giveaways found: {templist}")
        for i in templist:
            giveaway = self.active_giveaways[i]
            if giveaway["end_time"] - discord.utils.utcnow() <= timedelta():
                await self.choose_winner(giveaway)
            else:
                if not firstgiveaway:
                    firstgiveaway = giveaway
                if giveaway["end_time"] < firstgiveaway["end_time"]:
                    firstgiveaway = giveaway

        self.logger.debug(f"Checking for first giveaway, {firstgiveaway}")
        if firstgiveaway:
            self.logger.debug(f"Sleeping for: {firstgiveaway['end_time']}")
            await discord.utils.sleep_until(firstgiveaway["end_time"])
            self.logger.debug(f"Choosing winner for {firstgiveaway}")
            await self.choose_winner(firstgiveaway)
        else:
            self.giveaway_task.cancel()

    @giveaway_commands.command()
    @checks.mod_and_above()
    async def start(
        self,
        interaction: discord.Interaction,
        time: str,
        prize: str,
        winner_count: typing.Optional[
            app_commands.Range[
                int,
                1,
            ]
        ] = 1,
        sponsor: typing.Optional[discord.Member] = None,
        rigged: typing.Optional[bool] = True,
    ):
        """Starts a new giveaway

        Parameters
        ----------
        time: str
            Time (ex: 30m, 2d, 3hr)
        prize: str
            Prize(s) for the winners
        winner_count: int
            Number of winners (default: 1)
        sponsor: discord.Member
            Sponsor of the giveaway
        rigged: bool
            Is giveaway rigged/biased (default: True)
        """

        await interaction.response.defer(ephemeral=True)

        (time, _) = calc_time([time, ""])  # type: ignore
        if time == 0:
            return await interaction.edit_original_response(content="Time can't be 0")

        if time is None:
            return await interaction.edit_original_response(content="Invalid time syntax.")

        if sponsor is None:
            assert isinstance(interaction.user, discord.Member)
            sponsor = interaction.user

        fields = {
            "winners": f"> **Winners: {winner_count}**",
            "sponsor": f"> **{'Hosted' if sponsor.id == interaction.user.id else 'Sponsored'} by**\n> {sponsor.mention}",
        }

        time = discord.utils.utcnow() + timedelta(seconds=time)  # type: ignore

        embed = discord.Embed(
            title="Giveaway started!",
            timestamp=time,  # type: ignore
            colour=discord.Colour.green(),
        )
        riggedinfo = ""
        if rigged:
            riggedinfo = (
                "[rigged](https://discord.com/channels/414027124836532234/414452106129571842/714496884844134401)"
            )

        description = f"**{prize}**\nReact with 🎉 to join the {riggedinfo} giveaway\n"
        for field in fields:
            description += "\n" + fields[field]

        embed.description = description

        embed.set_footer(text="Giveaway Ends")

        assert isinstance(interaction.channel, discord.TextChannel)

        message = await interaction.channel.send(embed=embed)
        await message.add_reaction("🎉")

        doc = {
            "prize": prize,
            "end_time": time,
            "message_id": message.id,
            "channel_id": message.channel.id,
            "winners_no": winner_count,
            "winners": "",
            "rigged": rigged,
            "host": interaction.user.id,
            "sponsor": sponsor.id,
            "giveaway_over": False,
            "giveaway_cancelled": False,
        }

        self.active_giveaways[doc["message_id"]] = doc

        self.giveaway_db.insert_one(doc)

        if self.giveaway_task.is_running():
            self.giveaway_task.restart()
        else:
            self.giveaway_task.start()

        await interaction.edit_original_response(content="Giveaway started.")

    @giveaway_commands.command()
    @checks.mod_and_above()
    async def end(self, interaction: discord.Interaction, message_id: str):
        """Ends the giveaway preemptively

        Parameters
        ----------
        message_id: str
            Message ID of the giveaway embed.
        """

        await interaction.response.defer(ephemeral=True)

        try:
            message_id_ = int(message_id)
        except ValueError as ve:
            return await interaction.edit_original_response(content="Invalid message id.")

        if message_id_ in self.active_giveaways:
            await self.choose_winner(self.active_giveaways[message_id_])
            self.giveaway_task.restart()
            await interaction.edit_original_response(content=f"{Reference.Emoji.PartialString.kgsYes} Giveaway ended.")
            return

        await interaction.edit_original_response(content="Giveaway not found!")

    @giveaway_commands.command()
    @checks.mod_and_above()
    async def cancel(self, interaction: discord.Interaction, message_id: str):
        """Cancels the giveaway

        Parameters
        ----------
        message_id: str
            Message ID of the giveaway embed.
        """

        await interaction.response.defer(ephemeral=True)
        assert interaction.guild

        try:
            message_id_ = int(message_id)
        except ValueError as ve:
            return await interaction.edit_original_response(content="Invalid message id.")

        if message_id_ in self.active_giveaways:
            giveaway = self.active_giveaways[message_id_]

            try:
                message = await interaction.guild.get_channel(giveaway["channel_id"]).fetch_message(  # type: ignore
                    giveaway["message_id"]
                )
                await message.delete()
                del self.active_giveaways[message_id_]
                self.giveaway_task.restart()
                self.giveaway_db.update_one(giveaway, {"$set": {"giveaway_cancelled": True}})
                return await interaction.edit_original_response(
                    content=f"{Reference.Emoji.PartialString.kgsYes} Giveaway cancelled!"
                )
            except Exception as e:
                raise e

        await interaction.edit_original_response(content="Giveaway not found!")

    @giveaway_commands.command()
    @checks.mod_and_above()
    async def reroll(
        self,
        interaction: discord.Interaction,
        message_id: str,
        winner_count: typing.Optional[
            app_commands.Range[
                int,
                1,
            ]
        ] = None,
        rigged: typing.Optional[bool] = None,
    ):
        """Reroll the giveaway to select new winners.

        Parameters
        ----------
        message_id: str
            Message ID of giveaway embed
        winner_count: int
            Number of winners (default: Same as original roll)
        rigged: bool
            Is giveaway rigged/biased (default: Same as original roll)
        """

        await interaction.response.defer(ephemeral=True)

        try:
            message_id_ = int(message_id)
        except ValueError as ve:
            return await interaction.edit_original_response(content="Invalid message id.")
        doc = self.giveaway_db.find_one({"giveaway_over": True, "message_id": message_id_})
        if doc:
            if winner_count != None:
                doc["winners_no"] = winner_count
            if rigged != None:
                doc["rigged"] = rigged
            await self.choose_winner(doc)
            await interaction.edit_original_response(
                content=f"{Reference.Emoji.PartialString.kgsYes} Giveaway rerolled!"
            )
            return

        await interaction.edit_original_response(content="Giveaway not found!")

    @giveaway_commands.command()
    @checks.mod_and_above()
    async def list(self, interaction: discord.Interaction):
        """List all active giveaways"""

        embed = discord.Embed(title="Active giveaways:")
        for messageid in self.active_giveaways:
            giveaway = self.active_giveaways[messageid]
            try:
                time = int(giveaway["end_time"].timestamp())
                embed.add_field(
                    name=giveaway["prize"],
                    value=f"[Giveaway](https://discord.com/channels/414027124836532234/{giveaway['channel_id']}/{giveaway['message_id']}) ends in <t:{time}:R>",
                )
            except Exception as e:
                self.logger.exception(e)
                return await interaction.response.send_message("Error!!! Take a screenshot.", ephemeral=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: BirdBot):
    await bot.add_cog(Giveaway(bot))
