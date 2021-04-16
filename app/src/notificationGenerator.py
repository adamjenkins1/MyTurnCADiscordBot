import logging
import time
from datetime import datetime, timedelta

import pgeocode
import pymongo
import pytz

from .constants import NOTIFICATION_WAIT_PERIOD
from .myTurnCA import MyTurnCA


class NotificationGenerator:
    """Class to fulfill a requested notification"""
    def __init__(self, mongodb_user: str, mongodb_password: str, mongodb_host: str,
                 mongodb_port: str, my_turn_api_key: str):
        self.nomi = pgeocode.Nominatim('us')
        self.mongodb = pymongo.MongoClient(f'mongodb://{mongodb_user}:{mongodb_password}@{mongodb_host}:{mongodb_port}')
        self.my_turn_ca = MyTurnCA(api_key=my_turn_api_key)
        self.logger = logging.getLogger(__name__)

    def generate_notification(self, zip_code: int):
        """Checks if appointments are available near the given zip code and updates
        the notification document when they are found"""
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

            message = 'Hey <@{user_id}>, I found available openings at these locations from ' \
                      f'{start_date.strftime("%x")} to {end_date.strftime("%x")}, ' \
                      'go to https://myturn.ca.gov to make an appointment!\n'

            for appointment in appointments:
                message += f'  * {str(appointment.location)} - {len(appointment.slots)} appointment(s) available\n'

            self.logger.info(f'found appointments, updating notifications '
                             f'for zip_code {zip_code} with message - {message}')
            self.mongodb.my_turn_ca.notifications.update({'zip_code': zip_code}, {'$set': {'message': message}})
            return