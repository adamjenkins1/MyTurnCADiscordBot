"""Discord bot to help you find a COVID-19 vaccination appointment in CA"""
import logging
import multiprocessing
import queue
import time
from datetime import timedelta, datetime
from typing import Callable

import pgeocode
import pymongo
import pytz
from discord.errors import NotFound, Forbidden
from discord.ext import commands, tasks
from pandas import isnull, DataFrame

from .constants import COMMAND_PREFIX, BOT_DESCRIPTION, CANCEL_NOTIFICATION_BRIEF, CANCEL_NOTIFICATION_DESCRIPTION, \
    NOTIFY_BRIEF, NOTIFY_DESCRIPTION, GET_NOTIFICATIONS_DESCRIPTION, GET_LOCATIONS_DESCRIPTION, \
    GET_APPOINTMENTS_BRIEF, GET_APPOINTMENTS_DESCRIPTION, NOTIFICATION_WAIT_PERIOD
from .exceptions import InvalidZipCode
from .myTurnCA import MyTurnCA


class AppointmentNotification:
    """Class which stores required information for the bot to notify users of available appointments"""
    def __init__(self, channel_id: int, message: str, zip_code: int, user_id: int):
        self.channel_id = channel_id
        self.message = message
        self.user_id = user_id
        self.zip_code = zip_code


class NotificationProcess:
    """Class to represent a background notification process"""
    def __init__(self, process: multiprocessing.Process, target: Callable, kwargs: dict):
        self.process = process
        self.target = target
        self.kwargs = kwargs

    def __str__(self):
        return f'{self.process.pid}: {self.target.__name__}, {self.kwargs}'


class MyTurnCABot(commands.Bot):
    """Main bot class"""
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)
        self.worker_processes = {}

    async def close(self):
        """Cleans up worker processes to avoid leaving zombie processes on the host"""
        for worker in self.worker_processes.values():
            worker.process.kill()
            worker.process.join()

        await super().close()


def run(token: str, mongodb_user: str, mongodb_password: str, mongodb_host: str, mongodb_port: str):
    """Main bot driver method"""
    bot = MyTurnCABot(command_prefix=COMMAND_PREFIX, description=BOT_DESCRIPTION)
    logger = logging.getLogger(__name__)
    my_turn_ca = MyTurnCA()
    nomi = pgeocode.Nominatim('us')
    notification_queue = multiprocessing.Queue()
    mongodb = pymongo.MongoClient(f'mongodb://{mongodb_user}:{mongodb_password}@{mongodb_host}:{mongodb_port}')
    my_turn_ca_db = mongodb.my_turn_ca

    def is_zip_code_valid(zip_code_result: DataFrame):
        """Returns whether or not the provided DataFrame represents a valid CA zip code"""
        return not any([
            isnull(zip_code_result['latitude']),
            isnull(zip_code_result['longitude']),
            isnull(zip_code_result['state_code']),
            zip_code_result['state_code'] != 'CA'
        ])

    def add_notification_generator(channel_id: int, user_id: int, zip_code_query: DataFrame,
                                   result_queue: multiprocessing.Queue):
        """Function run by worker processes to notify users when available appointments are found"""
        while True:
            start_date = datetime.now(tz=pytz.timezone('US/Pacific')).date()
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
        """Bot command to cancel an outstanding notification"""
        notification = my_turn_ca_db.notifications.find_one({'user_id': ctx.author.id, 'zip_code': zip_code})
        if not notification:
            await ctx.reply(f'You don\'t have any outstanding notification requests for zip code {zip_code}')
            return

        my_turn_ca_db.notifications.delete_one(notification)
        await ctx.reply(f'Your notification request for zip code {zip_code} has been canceled, '
                        f'see `!help notify` to request another')

        bot.worker_processes[notification['pid']].process.kill()
        bot.worker_processes[notification['pid']].process.join()
        bot.worker_processes.pop(notification['pid'])

    @bot.command(brief=NOTIFY_BRIEF, description=NOTIFY_DESCRIPTION)
    async def notify(ctx: commands.Context, zip_code: int):
        """Bot command to request to be notified when appointments are available near the given zip code"""
        city = nomi.query_postal_code(zip_code)
        if not is_zip_code_valid(city):
            raise InvalidZipCode

        if my_turn_ca_db.notifications.find_one({'user_id': ctx.author.id}):
            await ctx.reply('You already have an outstanding notification request, '
                            'see `!help cancel_notification` to cancel it')
            return

        await ctx.reply(f'OK, I\'ll let you know when I find appointments in your area')
        kwargs = {
            'channel_id': ctx.channel.id,
            'user_id': ctx.author.id,
            'zip_code_query': city,
            'result_queue': notification_queue
        }
        worker = multiprocessing.Process(target=add_notification_generator, kwargs=kwargs)
        worker.start()
        bot.worker_processes[worker.pid] = NotificationProcess(process=worker,
                                                               target=add_notification_generator,
                                                               kwargs=kwargs)
        my_turn_ca_db.notifications.insert_one({
            'user_id': ctx.author.id,
            'zip_code': zip_code,
            'pid': worker.pid,
            'channel_id': ctx.channel.id
        })

    @bot.command(brief=GET_NOTIFICATIONS_DESCRIPTION, description=GET_NOTIFICATIONS_DESCRIPTION)
    async def get_notifications(ctx: commands.Context):
        """Bot command to retrieve a user's outstanding notifications"""
        notifications = list(my_turn_ca_db.notifications.find({'user_id': ctx.author.id}))
        if not notifications:
            await ctx.reply('You don\'t have any outstanding notification requests')
            return

        await ctx.reply(f'You\'ve asked to be notified when appointments become available near these zip codes '
                        f'- {", ".join([str(notification["zip_code"]) for notification in notifications])}')

    @tasks.loop(seconds=5)
    async def check_workers():
        # remove any worker processes that successfully exited
        [bot.worker_processes.pop(pid) for pid in [pid for pid in bot.worker_processes.keys()
                                                   if not bot.worker_processes[pid].process.is_alive()
                                                   and bot.worker_processes[pid].process.exitcode == 0]]

        # create replacement processes for those that failed
        failed_workers = [pid for pid in bot.worker_processes.keys() if not bot.worker_processes[pid].process.is_alive()
                          and bot.worker_processes[pid].process.exitcode != 0]
        if not failed_workers:
            return

        for pid in failed_workers:
            failed_worker = bot.worker_processes[pid]
            new_worker = multiprocessing.Process(target=failed_worker.target,
                                                 kwargs=failed_worker.kwargs)
            new_worker.start()
            bot.worker_processes[new_worker.pid] = NotificationProcess(process=new_worker,
                                                                       target=failed_worker.target,
                                                                       kwargs=failed_worker.kwargs)
            logger.info(f'Process {str(failed_worker)} failed, retrying with new process - '
                        f'{str(bot.worker_processes[new_worker.pid])}')
            my_turn_ca_db.notifications.update_one(
                {
                    'user_id': failed_worker.kwargs['user_id'],
                    'zip_code': int(failed_worker.kwargs['zip_code_query']['postal_code']),
                    'channel_id': failed_worker.kwargs['channel_id'],
                    'pid': pid
                },
                {
                    '$set': {'pid': new_worker.pid}
                }
            )

            bot.worker_processes.pop(pid)

    @tasks.loop(seconds=5)
    async def poll_notifications():
        """Background task to check if worker processes have populated the notification queue"""
        notification = object()
        try:
            notification = notification_queue.get(block=False)
            logger.info(f'found notification in queue, sending message to channel - {notification.__dict__}')
            channel = await bot.fetch_channel(notification.channel_id)
            await channel.send(notification.message)
            my_turn_ca_db.notifications.delete_one({
                'user_id': notification.user_id,
                'zip_code': notification.zip_code,
                'channel_id': notification.channel_id
            })
        except queue.Empty:
            pass
        except NotFound:
            logger.error(f'channel {notification.channel_id} was not found, maybe it was deleted...?')
        except Forbidden:
            logger.error(f'we don\'t have sufficient privileges to fetch channel {notification.channel_id}')

    @tasks.loop(seconds=10)
    async def start_tasks():
        """Task to start/restart other tasks should they fail"""
        [task.start() for task in [poll_notifications, check_workers] if not task.is_running()]

    @bot.command(brief=GET_LOCATIONS_DESCRIPTION, description=GET_LOCATIONS_DESCRIPTION)
    async def get_locations(ctx: commands.Context, zip_code: int):
        """Bot command to list available vaccination locations near the given zip code"""
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
        """Bot command to list available appointments at vaccination locations near the given zip code"""
        city = nomi.query_postal_code(zip_code)
        if not is_zip_code_valid(city):
            raise InvalidZipCode

        start_date = datetime.now(tz=pytz.timezone('US/Pacific')).date()
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
        """Bot command error handler to handle expected exceptions"""
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
        """General bot error handler to handle unexpected exceptions"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.reply(f'`{ctx.message.content}` isn\'t a valid command, see `!help` for supported commands')
            return

        if ctx.command.error:
            return

        raise error

    @bot.event
    async def on_ready():
        """Bot event to start background task and create worker processes to handle any outstanding notifications"""
        # stop running tasks to make sure we aren't crossing streams
        [task.stop() for task in [start_tasks, poll_notifications, check_workers] if task.is_running()]

        # if we disconnected and reconnected, kill old workers in case they got stuck
        for process in bot.worker_processes.values():
            process.kill()
            process.join()

        bot.worker_processes = {}
        # for every notification request that hasn't been fulfilled, create a new worker process
        notification_cursor = my_turn_ca_db.notifications.find()
        for notification in notification_cursor:
            kwargs = {
                'channel_id': notification['channel_id'],
                'user_id': notification['user_id'],
                'zip_code_query': nomi.query_postal_code(notification['zip_code']),
                'result_queue': notification_queue
            }
            worker = multiprocessing.Process(target=add_notification_generator, kwargs=kwargs)
            worker.start()
            bot.worker_processes[worker.pid] = NotificationProcess(process=worker,
                                                                   target=add_notification_generator,
                                                                   kwargs=kwargs)
            my_turn_ca_db.notifications.update_one({'_id': notification['_id']}, {'$set': {'pid': worker.pid}})

        start_tasks.start()
        notification_cursor.close()

    bot.run(token)