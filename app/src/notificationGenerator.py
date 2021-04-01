import logging
import time
from datetime import datetime, timedelta

import pgeocode
import pymongo
import pytz

from app.src.constants import NOTIFICATION_WAIT_PERIOD
from app.src.myTurnCA import MyTurnCA


class NotificationGenerator:
    def __init__(self, mongodb_user: str, mongodb_password: str, mongodb_host: str, mongodb_port: str):
        self.nomi = pgeocode.Nominatim('us')
        self.mongodb = pymongo.MongoClient(f'mongodb://{mongodb_user}:{mongodb_password}@{mongodb_host}:{mongodb_port}')
        self.my_turn_ca = MyTurnCA()
        self.logger = logging.getLogger(__name__)

    def generate_notification(self, channel_id: int, user_id: int, zip_code: int):
        """Function run by worker processes to notify users when available appointments are found"""
        zip_code_query = self.nomi.query_postal_code(zip_code)
        while True:
            start_date = datetime.now(tz=pytz.timezone('US/Pacific')).date()
            end_date = start_date + timedelta(weeks=1)
            appointments = self.my_turn_ca.get_appointments(latitude=zip_code_query['latitude'],
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

            self.logger.info(f'found appointments, updating DB document - channel_id = {channel_id}, '
                             f'user_id = {user_id}, message = {message}, zip_code = {zip_code}')

            self.mongodb.my_turn_ca.notifications.update_one(
                {
                    'user_id': user_id,
                    'zip_code': zip_code,
                    'channel_id': channel_id
                },
                {
                    '$set': {'message': message}
                }
            )

            return
