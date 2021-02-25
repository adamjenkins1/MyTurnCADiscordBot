import logging

from discord.ext import commands

from myTurnCA import MyTurnCA


def run(token: str):
    bot = commands.Bot(command_prefix='!', description='Bot to help you get a COVID-19 vaccination appointment in CA')
    logger = logging.getLogger(__name__)
    my_turn_ca = MyTurnCA()

    @bot.command()
    async def ping(ctx):
        logger.info('sending pong')
        await ctx.send('pong')

    @bot.command()
    async def get_locations(ctx, latitude: float, longitude: float):
        logger.debug(f'got latitude - {latitude} and longitude - {longitude}')
        locations = my_turn_ca.get_locations(latitude, longitude)
        logging.debug(f'got locations - {[str(x) for x in locations]}')

        if not locations:
            await ctx.send('Sorry, I didn\'t find any vaccination locations in your area')
            return

        message = 'Found these vaccination locations near you: \n'
        for location in locations:
            message += f'  * {str(location)}\n'

        await ctx.send(message)

    bot.run(token)