import discord
import datetime


def create_embed(author, users, action, reason, extra="None", color=discord.Color.blurple):
    """
        Author: Message sender. (eg: ctx.author)
        Users: List of users affected (Pass None if no users)
        Action: Action/Command
        Reason: Reason
        Extra: Additional Info
        Color: Color of the embed
    """
    n1 = "\n"

    user_str = None
    if users is not None:

        for u in users:
            user_str = user_str + f'{ u.name }#{ u.discriminator }  ({ u.id })' + "\n"

    embed = discord.Embed(title=f'{author.name}#{author.discriminator}', description=f'{author.id}', color=color)
    embed.add_field(name='User(s) Affected ', value=f'```{ user_str }```', inline=False)
    embed.add_field(name='Action',value=f'```{ action }```', inline=False)
    embed.add_field(name='Reason', value=f'```{ reason }```', inline=False)
    embed.add_field(name='Additional Info', value=f'```{ extra }```', inline=False)
    embed.set_footer(text=datetime.datetime.utcnow())

    return embed