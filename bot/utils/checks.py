# bot/utils/checks.py
from discord.ext import commands

AUTHORIZED_USER_ID = 123456789012345678  # Replace with actual user ID

def is_owner_or_authorized_user():
    async def predicate(ctx):
        return (
            await ctx.bot.is_owner(ctx.author)
            or ctx.author.id == AUTHORIZED_USER_ID
        )
    return commands.check(predicate)
