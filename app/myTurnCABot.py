import logging
from datetime import date
from dateutil.relativedelta import relativedelta

from discord.ext import commands

from myTurnCA import MyTurnCA


def run(token: str):
    bot = commands.Bot(command_prefix='!', description='Bot to help you get a COVID-19 vaccination appointment in CA')
    logger = logging.getLogger(__name__)
    my_turn_ca = MyTurnCA()

    @bot.command()
    async def get_locations(ctx, latitude: float, longitude: float):
        logger.info(f'got latitude - {latitude} and longitude - {longitude}')
        locations = my_turn_ca.get_locations(latitude, longitude)
        logger.info(f'got locations - {[str(x) for x in locations]}')

        if not locations:
            await ctx.send('Sorry, I didn\'t find any vaccination locations in your area')
            return

        message = 'Found these vaccination locations near you: \n'
        for location in locations:
            message += f'  * {str(location)}\n'

        await ctx.send(message)

    @bot.command()
    async def get_location_availability(ctx, location_id: str, location_latitude: float, location_longitude: float):
        logger.info(f'got location_id - {location_id}, location_latitude - {location_latitude}, '
                    f'location_longitude - {location_longitude}')
        locations = my_turn_ca.get_locations(location_latitude, location_longitude)
        logger.info(f'got locations - {[str(x) for x in locations]}')

        desired_location = [x for x in locations if x.location_id == location_id]
        if not desired_location:
            await ctx.send(f'Sorry, I did\'t find location {location_id} near those coordinates')
            return

        start_date = date.today()
        end_date = start_date + relativedelta(weeks=+1)
        location_availability = my_turn_ca.get_availability(location_id=location_id,
                                                            start_date=start_date,
                                                            end_date=end_date,
                                                            vaccine_data=desired_location[0].vaccine_data)
        logger.info(f'got location availability {str(location_availability)}')

        slots = [item for sublist in [my_turn_ca.get_slots(location_id=location_id, start_date=x.date,
                                                           vaccine_data=desired_location[0].vaccine_data).slots
                                      for x in location_availability.dates_available] for item in sublist]
        if not slots:
            await ctx.send(f'Sorry, {desired_location[0].name} doesn\'t have any openings from '
                           f'{start_date.strftime("%x")} to {end_date.strftime("%x")}')
            return

        message = f'Found these slots at {desired_location[0].name}, go to https://myturn.ca.gov to make an appointment!\n'
        for slot in slots:
            message += f'  * {slot.local_start_time.strftime("%x %X")}\n'

        await ctx.send(message)

    bot.run(token)