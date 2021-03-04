import logging
import multiprocessing
import queue
import time
from datetime import date, timedelta

import pgeocode
import pymongo
from discord.ext import commands, tasks
from pandas import isnull, DataFrame

from .appointmentNotification import AppointmentNotification
from .constants import COMMAND_PREFIX, BOT_DESCRIPTION, CANCEL_NOTIFICATION_BRIEF, CANCEL_NOTIFICATION_DESCRIPTION, \
    NOTIFY_BRIEF, NOTIFY_DESCRIPTION, GET_NOTIFICATIONS_DESCRIPTION, GET_LOCATIONS_DESCRIPTION, \
    GET_APPOINTMENTS_BRIEF, GET_APPOINTMENTS_DESCRIPTION, NOTIFICATION_WAIT_PERIOD
from .exceptions import InvalidZipCode
from .myTurnCA import MyTurnCA


class MyTurnCABot(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)
        self.worker_processes = {}

    async def close(self):
        for process in self.worker_processes.values():
            process.kill()
            process.join()

        await super().close()


def run(token: str, mongodb_user: str, mongodb_password: str, mongodb_host: str, mongodb_port: str):
    bot = MyTurnCABot(command_prefix=COMMAND_PREFIX, description=BOT_DESCRIPTION)
    logger = logging.getLogger(__name__)
    my_turn_ca = MyTurnCA()
    nomi = pgeocode.Nominatim('us')
    reminder_queue = multiprocessing.Queue()
    mongodb = pymongo.MongoClient(f'mongodb://{mongodb_user}:{mongodb_password}@{mongodb_host}:{mongodb_port}')
    my_turn_ca_db = mongodb.my_turn_ca

    def is_zip_code_valid(zip_code_result: DataFrame):
        return not any([
            isnull(zip_code_result['latitude']),
            isnull(zip_code_result['longitude']),
            isnull(zip_code_result['state_code']),
            zip_code_result['state_code'] != 'CA'
        ])

    def add_notification_generator(channel_id: int, user_id: int, zip_code_query: DataFrame,
                                   result_queue: multiprocessing.Queue):
        while True:
            start_date = date.today()
            end_date = start_date + timedelta(weeks=1)
            appointments = my_turn_ca.get_appointments(latitude=zip_code_query['latitude'],
                                                       longitude=zip_code_query['longitude'],
                                                       start_date=start_date, end_date=end_date)
            if not appointments:
                time.sleep(NOTIFICATION_WAIT_PERIOD)
                continue

            message = f'Hey <@{user_id}>, I found available openings at these locations from ' \
                      f'{start_date.strftime("%x")} to {end_date.strftime("%x")}, ' \
                      f'go to https://myturn.ca.gov to make an appointment!\n'

            for appointment in appointments:
                message += f'  * {str(appointment.location)} - {len(appointment.slots)} appointment(s) available\n'

            logger.info('found appointments, pushing onto queue')
            result_queue.put(AppointmentNotification(channel_id=channel_id,
                                                     message=message,
                                                     zip_code=int(zip_code_query['postal_code']),
                                                     user_id=user_id))
            return

    @bot.command(brief=CANCEL_NOTIFICATION_BRIEF, description=CANCEL_NOTIFICATION_DESCRIPTION)
    async def cancel_notification(ctx: commands.Context, zip_code: int):
        notification = my_turn_ca_db.notifications.find_one({'user_id': ctx.author.id, 'zip_code': zip_code})
        if not notification:
            await ctx.reply(f'You don\'t have any outstanding notification requests for zip code {zip_code}')
            return

        my_turn_ca_db.notifications.delete_one(notification)
        await ctx.reply(f'Your notification request for zip code {zip_code} has been canceled, '
                        f'see `!help notify` to request another')

        bot.worker_processes[notification['pid']].kill()
        bot.worker_processes[notification['pid']].join()

    @bot.command(brief=NOTIFY_BRIEF, description=NOTIFY_DESCRIPTION)
    async def notify(ctx: commands.Context, zip_code: int):
        city = nomi.query_postal_code(zip_code)
        if not is_zip_code_valid(city):
            raise InvalidZipCode

        if my_turn_ca_db.notifications.find_one({'user_id': ctx.author.id}):
            await ctx.reply('You already have an outstanding notification request, '
                            'see `!help cancel_notification` to cancel it')
            return

        await ctx.reply(f'OK, I\'ll let you know when I find appointments in your area')
        worker = multiprocessing.Process(target=add_notification_generator,
                                         args=(ctx.channel.id, ctx.author.id, city, reminder_queue))
        worker.start()
        bot.worker_processes[worker.pid] = worker
        my_turn_ca_db.notifications.insert_one({
            'user_id': ctx.author.id,
            'zip_code': zip_code,
            'pid': worker.pid,
            'channel_id': ctx.channel.id
        })

    @bot.command(brief=GET_NOTIFICATIONS_DESCRIPTION, description=GET_NOTIFICATIONS_DESCRIPTION)
    async def get_notifications(ctx: commands.Context):
        notifications = list(my_turn_ca_db.notifications.find({'user_id': ctx.author.id}))
        if not notifications:
            await ctx.reply('You don\'t have any outstanding notification requests')
            return

        await ctx.reply(f'You\'ve asked to be notified when appointments become available near these zip codes '
                        f'- {", ".join([str(notification["zip_code"]) for notification in notifications])}')

    @tasks.loop(seconds=5)
    async def poll_notifications():
        [bot.worker_processes.pop(pid) for pid in [pid for pid in bot.worker_processes.keys()
                                                   if not bot.worker_processes[pid].is_alive()]]

        try:
            notification = reminder_queue.get(block=False)
            logger.info(f'found notification in queue, sending message to channel - {notification.__dict__}')
            channel = bot.get_channel(notification.channel_id)
            my_turn_ca_db.notifications.delete_one({
                'user_id': notification.user_id,
                'zip_code': notification.zip_code,
                'channel_id': notification.channel_id
            })

            if channel is None:
                logger.info(f'channel {notification.channel_id} does not exist, maybe it was deleted...?')
                return

            await channel.send(notification.message)
        except queue.Empty:
            pass

    @bot.command(brief=GET_LOCATIONS_DESCRIPTION, description=GET_LOCATIONS_DESCRIPTION)
    async def get_locations(ctx: commands.Context, zip_code: int):
        city = nomi.query_postal_code(zip_code)
        if not is_zip_code_valid(city):
            raise InvalidZipCode

        locations = my_turn_ca.get_locations(city['latitude'], city['longitude'])
        if not locations:
            await ctx.reply('Sorry, I didn\'t find any vaccination locations in your area')
            return

        message = 'Found these vaccination locations near you: \n'
        for location in locations:
            message += f'  * {str(location)}\n'

        await ctx.reply(message)

    @bot.command(brief=GET_APPOINTMENTS_BRIEF, description=GET_APPOINTMENTS_DESCRIPTION)
    async def get_appointments(ctx: commands.Context, zip_code: int):
        city = nomi.query_postal_code(zip_code)
        if not is_zip_code_valid(city):
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
    @notify.error
    @get_notifications.error
    @cancel_notification.error
    async def command_error_handler(ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.TooManyArguments) or isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(str(error))
            return
        if isinstance(error, InvalidZipCode):
            await ctx.reply(f'Provided zip code doesn\'t exist in California')
            return
        if isinstance(error, commands.BadArgument):
            await ctx.reply(f'Provided zip code must be a valid integer, see `!help {ctx.command.name}`')
            return

        raise error

    @bot.event
    async def on_command_error(ctx: commands.Context, error: commands.UserInputError):
        if isinstance(error, commands.CommandNotFound):
            await ctx.reply(f'`{ctx.message.content}` isn\'t a valid command, see `!help` for supported commands')
            return

        if ctx.command.error:
            return

        raise error

    @bot.event
    async def on_ready():
        if not poll_notifications.is_running():
            poll_notifications.start()

        notification_cursor = my_turn_ca_db.notifications.find()
        for notification in notification_cursor:
            if notification['pid'] not in bot.worker_processes:
                worker = multiprocessing.Process(target=add_notification_generator,
                                                 args=(notification['channel_id'],
                                                       notification['user_id'],
                                                       nomi.query_postal_code(notification['zip_code']),
                                                       reminder_queue))
                worker.start()
                bot.worker_processes[worker.pid] = worker
                my_turn_ca_db.notifications.update_one({'_id': notification['_id']}, {'$set': {'pid': worker.pid}})

        notification_cursor.close()

    bot.run(token)