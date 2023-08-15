
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

        patreon_3 = 753258289185161248
        patreon_2 = 415154206970740737
        patreon_1 = 753268671107039274

        galacduck = 698479120878665729 # GalacDuck
        legendary_duck = 662937489220173884 # LegendDuck
        super_duck = 637114917178048543 # SuperDuck
        duck = 637114897544511488 # Duck
        smol_duck = 637114873268142081 # Smol Duck
        duckling = 637114849570062347 # Duckling
        duck_hatchling = 637114722675851302 # Duck Hatchling
        duck_egg = 821961644425871390 # Duck Egg

        @classmethod
        def admin_and_above(cls):
            return [
                cls.administrator, 
                cls.kgsofficial
            ]

        @classmethod
        def moderator_and_above(cls):
            return [
                cls.trainee_mod,
                cls.moderator, 
                cls.administrator, 
                cls.kgsofficial
            ]
        
        @classmethod
        def patreon(cls):
            return [
                cls.patreon_1,
                cls.patreon_2,
                cls.patreon_3
            ]

    class Categories:
        moderation = 414095379156434945
        server_logs = 879399341561892905

    class Channels:
        general = 414027124836532236
        bot_commands = 414452106129571842
        bot_tests = 414179142020366336
        new_members = 526882555174191125
        humanities = 546315063745839115
        server_moments = 960927545639972994
        mod_chat = 1092578562608988290
        social_media_queue = 580354435302031360
        social_media_feed = 489450008643502080
        banners_and_topics = 546689491486769163
        intro_channel = 981620309163655218
        language_tests = 974333356688965672

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

        @classmethod
        async def fetch(cls, client: discord.Client, ref:int) -> discord.Emoji:
            """
            When given a client object and an emoji id, returns a discord.Emoji
            """
            
            return await client.fetch_emoji(ref)

# TODO: MISC.py still has some raw ids
# TODO: roleassign.py still has raw data (delete instead?)
# TODO: GLOBAL_LISTENERS.py still has raw data
# TODO: GIVEAWAY.py still has raw data
