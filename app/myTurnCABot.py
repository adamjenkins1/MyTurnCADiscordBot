import logging

from discord.ext import commands


def run(token: str):
    bot = commands.Bot(command_prefix='!')
    logger = logging.getLogger(__name__)

    @bot.command()
    async def ping(ctx):
        logger.info('sending pong')
        await ctx.send('pong')

    bot.run(token)