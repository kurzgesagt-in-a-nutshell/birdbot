"""
This module contains the configuration settings for guild level items such as roles, channels and emojis.
"""

import discord


class Reference:
    botownerlist = [
        183092910495891467,  # Sloth
        248790213386567680,  # Austin
    ]
    botdevlist = [
        389718094270038018,  # FC
        424843380342784011,  # Oeav
        183092910495891467,  # Sloth
        248790213386567680,  # Austin
        229779964898181120,  # source
    ]
    guild = 414027124836532234
    mainbot = 471705718957801483
    bannsystembot = 697374082509045800

    class Roles:

        moderator = 414092550031278091
        administrator = 414029841101225985
        kgsofficial = 414954904382210049
        trainee_mod = 905510680763969536
        robobird = 414155501518061578
        stealthbot = 691931822023770132
        subreddit_mod = 681812574026727471
        kgsmaintenance = 915629257470906369

        patreon_3 = 753258289185161248
        patreon_2 = 415154206970740737
        patreon_1 = 753268671107039274

        nitro_bird = 598031301622104095
        contributor = 476852559311798280

        galacduck = 698479120878665729  # GalacDuck
        legendary_duck = 662937489220173884  # LegendDuck
        super_duck = 637114917178048543  # SuperDuck
        duck = 637114897544511488  # Duck
        smol_duck = 637114873268142081  # Smol Duck
        duckling = 637114849570062347  # Duckling
        duck_hatchling = 637114722675851302  # Duck Hatchling
        duck_egg = 821961644425871390  # Duck Egg

        english = 901136119863844864

        @staticmethod
        def admin_and_above():
            return [Reference.Roles.administrator, Reference.Roles.kgsofficial]

        @staticmethod
        def moderator_and_above():
            return [
                Reference.Roles.trainee_mod,
                Reference.Roles.moderator,
                Reference.Roles.administrator,
                Reference.Roles.kgsofficial,
            ]

        @staticmethod
        def patreon():
            return [Reference.Roles.patreon_1, Reference.Roles.patreon_2, Reference.Roles.patreon_3]

    class Categories:
        moderation = 414095379156434945
        server_logs = 879399341561892905

    class Channels:
        general = 1162035011025911889
        bot_commands = 414452106129571842
        bot_tests = 414179142020366336
        new_members = 526882555174191125
        humanities = 1162034723758034964
        server_moments = 960927545639972994
        mod_chat = 1092578562608988290
        social_media_queue = 580354435302031360
        social_media_feed = 489450008643502080
        banners_and_topics = 546689491486769163
        intro_channel = 981620309163655218
        language_tests = 974333356688965672
        the_perch = 651461159995834378

        class Logging:
            mod_actions = 543884016282239006
            automod_actions = 966769038879498301
            message_actions = 879399217511161887
            member_actions = 939570758903005296
            dev = 865321589919055882
            misc_actions = 713107972737204236
            bannsystem = 1009138597221372044

    class Emoji:
        kgsYes = 955703069516128307
        kgsNo = 955703108565098496

        class PartialString:
            kgsYes = "<:kgsYes:955703069516128307>"
            kgsNo = "<:kgsNo:955703108565098496>"
            kgsStop = "<:kgsStop:579824947959169024>"
            kgsWhoAsked = "<:kgsWhoAsked:754871694467924070>"

        @staticmethod
        async def fetch(client: discord.Client, ref: int) -> discord.Emoji | None:
            """
            When given a client object and an emoji id, returns a discord.Emoji
            """

            if em := client.get_emoji(ref) is not None:
                return em  # type: ignore
            return None


class GiveawayBias:
    roles = [
        {
            "id": Reference.Roles.galacduck,
            "bias": 11,
        },
        {
            "id": Reference.Roles.legendary_duck,
            "bias": 7,
        },
        {
            "id": Reference.Roles.super_duck,
            "bias": 4,
        },
        {
            "id": Reference.Roles.duck,
            "bias": 3,
        },
        {
            "id": Reference.Roles.smol_duck,
            "bias": 2,
        },
    ]
    default = 1


class ExclusiveColors:
    """
    Contains a list of selectable colored roles that can be provided to a user if they have the role that unlocks the color.
    """

    exclusive_colors = {
        "Patreon Orange": {
            "id": 976158045639946300,
            "unlockers": [Reference.Roles.patreon_1, Reference.Roles.patreon_2, Reference.Roles.patreon_3],
        },
        "Patreon Green": {
            "id": 976158006616137748,
            "unlockers": [Reference.Roles.patreon_2, Reference.Roles.patreon_3],
        },
        "Patreon Blue": {"id": 976157262718582784, "unlockers": [Reference.Roles.patreon_3]},
        "Nitro Pink": {"id": 976157185971204157, "unlockers": [Reference.Roles.nitro_bird]},
        "Contributor Gold": {"id": 976176253826654329, "unlockers": [Reference.Roles.contributor]},
    }
