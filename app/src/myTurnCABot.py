"""Discord bot to help you find a COVID-19 vaccination appointment in CA"""
import logging
import time
from datetime import timedelta, datetime

import pgeocode
import pymongo
import pytz
from discord.errors import NotFound, Forbidden
from discord.ext import commands, tasks
from pandas import isnull, DataFrame
from kubernetes import client, config

from .constants import COMMAND_PREFIX, BOT_DESCRIPTION, CANCEL_NOTIFICATION_BRIEF, CANCEL_NOTIFICATION_DESCRIPTION, \
    NOTIFY_BRIEF, NOTIFY_DESCRIPTION, GET_NOTIFICATIONS_DESCRIPTION, GET_LOCATIONS_DESCRIPTION, \
    GET_APPOINTMENTS_BRIEF, GET_APPOINTMENTS_DESCRIPTION, NOTIFICATION_WAIT_PERIOD, WORKER_PROCESS_DELAY, MONGO_USER, \
    MONGO_PASSWORD, MONGO_HOST, MONGO_PORT
from .exceptions import InvalidZipCode
from .myTurnCA import MyTurnCA


class MyTurnCABot(commands.Bot):
    """Main bot class"""
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)


def run(token: str, namespace: str, job_image: str, mongodb_user: str,
        mongodb_password: str, mongodb_host: str, mongodb_port: str):
    """Main bot driver method"""
    bot = MyTurnCABot(command_prefix=COMMAND_PREFIX, description=BOT_DESCRIPTION)
    config.load_incluster_config()
    k8s_batch = client.BatchV1Api()
    logger = logging.getLogger(__name__)
    my_turn_ca = MyTurnCA()
    nomi = pgeocode.Nominatim('us')
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

    @bot.command(brief=CANCEL_NOTIFICATION_BRIEF, description=CANCEL_NOTIFICATION_DESCRIPTION)
    async def cancel_notification(ctx: commands.Context, zip_code: int):
        """Bot command to cancel an outstanding notification"""
        notification = my_turn_ca_db.notifications.find_one({'user_id': ctx.author.id, 'zip_code': zip_code})
        if not notification:
            await ctx.reply(f'You don\'t have any outstanding notification requests for zip code {zip_code}')
            return

        # TODO delete k8s job
        my_turn_ca_db.notifications.delete_one(notification)
        await ctx.reply(f'Your notification request for zip code {zip_code} has been canceled, '
                        f'see `!help notify` to request another')

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
        job = k8s_batch.create_namespaced_job(
            namespace=namespace,
            body=client.V1Job(
                api_version='batch/v1',
                kind='Job',
                metadata=client.V1ObjectMeta(generate_name='notification-job-'),
                spec=client.V1JobSpec(
                    ttl_seconds_after_finished=0,
                    template=client.V1PodTemplateSpec(
                        spec=client.V1PodSpec(
                            restart_policy='OnFailure',
                            containers=[client.V1Container(
                                name='worker',
                                image=job_image,
                                args=[
                                    '--worker',
                                    '--channel_id',
                                    str(ctx.channel.id),
                                    '--user_id',
                                    str(ctx.author.id),
                                    '--zip_code',
                                    str(zip_code)
                                ],
                                env=[
                                    client.V1EnvVar(
                                        name=key,
                                        value=value
                                    )
                                    for key, value in {
                                        MONGO_USER: mongodb_user,
                                        MONGO_PASSWORD: mongodb_password,
                                        MONGO_HOST: mongodb_host,
                                        MONGO_PORT: mongodb_port
                                    }.items()
                                ]
                            )]
                        )
                    )
                )
            )
        )

        my_turn_ca_db.notifications.insert_one({
            'user_id': ctx.author.id,
            'zip_code': zip_code,
            'job_name': job.metadata.name,
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
    async def poll_notifications():
        """Background task to check if worker processes have populated the notification queue"""
        notification = None
        try:
            notification = my_turn_ca_db.notifications.find_one({'message': {'$exists': True}})
            if notification is None:
                return

            logger.info(f'found populated notification in database, sending message to channel - {notification}')
            channel = await bot.fetch_channel(notification['channel_id'])
            await channel.send(notification['message'])
            my_turn_ca_db.notifications.delete_one({'_id': notification['_id']})
        except NotFound:
            logger.error(f'channel {notification["channel_id"]} was not found, maybe it was deleted...?')
        except Forbidden:
            logger.error(f'we don\'t have sufficient privileges to fetch channel {notification["channel_id"]}')
        except Exception as e:
            logger.error('got unrecognized exception, silently catching it to avoid breaking loop')
            logger.error(e)

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
        if not poll_notifications.is_running():
            poll_notifications.start()

    bot.run(token)