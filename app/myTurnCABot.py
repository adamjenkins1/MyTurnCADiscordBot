import logging
import multiprocessing
import queue
import time
import pandas
from datetime import date, timedelta

import pgeocode
from discord.ext import commands, tasks

from myTurnCA import MyTurnCA


class Reminder:
    def __init__(self, channel_id: commands.Context, message: str):
        self.channel_id = channel_id
        self.message = message


class InvalidZipCode(commands.BadArgument):
    pass


def run(token: str):
    bot = commands.Bot(command_prefix='!', description='Bot to help you get a COVID-19 vaccination appointment in CA')
    logger = logging.getLogger(__name__)
    my_turn_ca = MyTurnCA()
    nomi = pgeocode.Nominatim('us')
    reminder_queue = multiprocessing.Queue()

    def add_reminder(ctx: commands.Context, result_queue: multiprocessing.Queue):
        print('running...')
        time.sleep(10)
        # result_queue.put(f'Hey {ctx.author.mention}, this is your reminder!')
        # result_queue.put(Reminder(ctx=ctx, message=f'Hey {ctx.author.mention}, this is your reminder!'))
        # result_queue.put(f'Hey {ctx.author.mention}, this is your reminder!')
        result_queue.put(Reminder(channel_id=ctx.channel.id, message=f'Hey {ctx.author.mention}, this is your reminder!'))
        print('put reminder in queue')

    @bot.command()
    async def set_reminder(ctx: commands.Context):
        worker = multiprocessing.Process(target=add_reminder, args=(ctx, reminder_queue))
        worker.start()
        await ctx.reply(f'OK {ctx.author.mention}, I\'ll remind you in 10 seconds')
        get_reminders.start()

    @tasks.loop(seconds=5)
    async def get_reminders():
        print('running loop...')
        try:
            reminder = reminder_queue.get(block=False)
            print(f'found reminder in queue - {reminder}')
            await bot.get_channel(reminder.channel_id).send(reminder.message)
        except queue.Empty:
            print('queue was empty')

    @bot.command()
    async def hello(ctx: commands.Context):
        await ctx.reply(f'Hi {ctx.author.mention}!')

    @bot.command()
    async def get_locations(ctx: commands.Context, zip_code: int):
        city = nomi.query_postal_code(zip_code)
        if pandas.isnull(city['latitude']) or pandas.isnull(city['longitude']):
            raise InvalidZipCode

        locations = my_turn_ca.get_locations(city['latitude'], city['longitude'])
        if not locations:
            await ctx.reply('Sorry, I didn\'t find any vaccination locations in your area')
            return

        message = 'Found these vaccination locations near you: \n'
        for location in locations:
            message += f'  * {str(location)}\n'

        await ctx.reply(message)

    @bot.command()
    async def get_appointments(ctx: commands.Context, zip_code: int):
        city = nomi.query_postal_code(zip_code)
        if pandas.isnull(city['latitude']) or pandas.isnull(city['longitude']):
            raise InvalidZipCode

        start_date = date.today()
        end_date = start_date + timedelta(weeks=1)
        appointments = my_turn_ca.get_appointments(latitude=city['latitude'], longitude=city['longitude'],
                                                   start_date=start_date, end_date=end_date)
        if not appointments:
            await ctx.reply('Sorry, I didn\'t find any vaccination appointments in your area')
            return

        message = f'Found available openings at these locations from ' \
                  f'{start_date.strftime("%x")} to {end_date.strftime("%x")}, ' \
                  f'go to https://myturn.ca.gov to make an appointment!\n'

        for appointment in appointments:
            message += f'  * {str(appointment.location)} - {len(appointment.slots)} appointment(s) available\n'

        await ctx.reply(message)

    @get_locations.error
    @get_appointments.error
    async def command_error_handler(ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.TooManyArguments) or isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(str(error))
            return
        if isinstance(error, InvalidZipCode):
            await ctx.reply(f'Provided zip code doesn\'t exist in the United States')
            return
        if isinstance(error, commands.BadArgument):
            await ctx.reply(f'Provided zip code must be a valid integer, see `!help {ctx.command.name}`')
            return

        raise error

    @bot.event
    async def on_command_error(ctx, error):
        if ctx.command:
            return

        if isinstance(error, commands.CommandNotFound):
            await ctx.reply(f'`{ctx.message.content}` isn\'t a valid command, see `!help` for supported commands')
            return

        raise error

    bot.run(token)