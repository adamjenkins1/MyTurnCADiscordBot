"""Python API wrapper around My Turn CA API"""
import functools
import json
import logging
import operator
from datetime import date, datetime
from typing import List

import pytz
from requests.adapters import HTTPAdapter
from requests.models import Response
from requests_toolbelt.sessions import BaseUrlSession

from .constants import MY_TURN_URL, ELIGIBLE_REQUEST_BODY, DEFAULT_RETRY_STRATEGY, ELIGIBILITY_URL, LOCATIONS_URL, \
    LOCATION_AVAILABILITY_URL, LOCATION_AVAILABILITY_SLOTS_URL, JSON_DECODE_ERROR_MSG, GOOD_BOT_HEADER, \
    REQUEST_HEADERS, LOCATION_POOLS


class Location:
    """Class to represent a vaccination location"""
    def __init__(self, location_id: str, name: str, booking_type: str, vaccine_data: str,
                 distance: float, address: str):
        self.location_id = location_id
        self.name = name
        self.booking_type = booking_type
        self.vaccine_data = vaccine_data
        self.distance_in_meters = distance
        self.address = address

    def __eq__(self, other):
        return self.location_id == other.location_id \
               and self.name == other.name \
               and self.booking_type == other.booking_type \
               and self.vaccine_data == other.vaccine_data \
               and self.distance_in_meters == other.distance_in_meters \
               and self.address == other.address

    def __str__(self):
        return f'{self.name} {self.distance_in_meters * 0.000621:.2f} mile(s) away'


class LocationAvailability:
    """Class to represent a vaccination location's availability"""
    def __eq__(self, other):
        return self.location == other.location and self.dates_available == other.dates_available

    def __init__(self, location: Location, dates_available: List[date]):
        self.location = location
        self.dates_available = dates_available


class LocationAvailabilitySlots:
    """Class to represent individual available appointments at a given vaccination location"""
    def __init__(self, location: Location, slots: List[datetime]):
        self.location = location
        self.slots = slots

    def __eq__(self, other):
        return self.location == other.location and self.slots == other.slots


class MyTurnCA:
    """Main API class"""
    def __init__(self, api_key: str):
        self.logger = logging.getLogger(__name__)
        self.session = BaseUrlSession(base_url=MY_TURN_URL)
        self.session.mount('https://', HTTPAdapter(max_retries=DEFAULT_RETRY_STRATEGY))
        self.session.headers.update({**REQUEST_HEADERS, GOOD_BOT_HEADER: api_key})
        self.vaccine_data = self._get_vaccine_data()

    def _get_vaccine_data(self) -> str:
        """Retrieve initial vaccine data"""
        response = self._send_request(url=ELIGIBILITY_URL, body=ELIGIBLE_REQUEST_BODY).json()
        if response['eligible'] is False:
            raise RuntimeError('something is wrong, default /eligibility body returned \'eligible\' = False')

        return response['vaccineData']

    def get_locations(self, latitude: float, longitude: float) -> List[Location]:
        """Gets available locations near the given coordinates"""
        body = {
            'location': {
                'lat': latitude,
                'lng': longitude
            },
            'fromDate': datetime.now(tz=pytz.timezone('US/Pacific')).strftime('%Y-%m-%d'),
            'vaccineData': self.vaccine_data,
            'locationQuery': {
                'includePools': LOCATION_POOLS
            }
        }

        response = self._send_request(url=LOCATIONS_URL, body=body)
        try:
            return [Location(location_id=x['extId'], name=x['name'], address=x['displayAddress'], booking_type=x['type'],
                             vaccine_data=x['vaccineData'], distance=x['distanceInMeters'])
                    for x in response.json()['locations']]
        except json.JSONDecodeError:
            self.logger.error(JSON_DECODE_ERROR_MSG.format(body=response.text))
            return []

    def get_availability(self, location: Location, start_date: date, end_date: date) -> LocationAvailability:
        """Gets a given vaccination location's availability"""
        body = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'vaccineData': location.vaccine_data,
            'doseNumber': 1
        }

        response = self._send_request(url=LOCATION_AVAILABILITY_URL.format(location_id=location.location_id), body=body)
        try:
            return LocationAvailability(location=location,
                                        dates_available=[datetime.strptime(x['date'], '%Y-%m-%d').date()
                                                         for x in response.json()['availability'] if x['available'] is True])
        except json.JSONDecodeError:
            self.logger.error(JSON_DECODE_ERROR_MSG.format(body=response.text))
            return LocationAvailability(location=location, dates_available=[])

    def get_slots(self, location: Location, start_date: date) -> LocationAvailabilitySlots:
        """Gets a given location's available appointments"""
        body = {
            'vaccineData': location.vaccine_data
        }

        response = self._send_request(url=LOCATION_AVAILABILITY_SLOTS_URL.format(location_id=location.location_id,
                                                                                 start_date=start_date.strftime('%Y-%m-%d')),
                                      body=body)
        try:
            return LocationAvailabilitySlots(location=location,
                                             slots=[self._combine_date_and_time(start_date, x['localStartTime'])
                                                    for x in response.json()['slotsWithAvailability']
                                                    if self._combine_date_and_time(start_date, x['localStartTime']) > datetime.now(tz=pytz.timezone('US/Pacific'))])
        except json.JSONDecodeError:
            self.logger.error(JSON_DECODE_ERROR_MSG.format(body=response.text))
            return LocationAvailabilitySlots(location=location, slots=[])

    def get_appointments(self, latitude: float, longitude: float, start_date: date, end_date: date) -> List[LocationAvailabilitySlots]:
        """Retrieves available appointments from all vaccination locations near the given coordinates"""
        locations = self.get_locations(latitude=latitude, longitude=longitude)
        if not locations:
            return []

        if start_date > end_date:
            raise ValueError('Provided start_date must be before end_date')

        appointments = []
        for location in locations:
            days_available = self.get_availability(location=location, start_date=start_date, end_date=end_date).dates_available
            if not days_available:
                continue

            location_appointments = [location_appointment for location_appointment in
                                     [self.get_slots(location=location, start_date=day_available)
                                      for day_available in days_available] if location_appointment.slots]
            if not location_appointments:
                continue

            # combines appointments on different days for the same location
            appointments.append(LocationAvailabilitySlots(location=location_appointments[0].location,
                                                          slots=functools.reduce(operator.add,
                                                                                 [location_appointment.slots for location_appointment in location_appointments])))

        return appointments

    @staticmethod
    def _combine_date_and_time(start_date: date, timestamp: str) -> datetime:
        """Private helper function to combine a date and timestamp"""
        return datetime.combine(start_date, datetime.strptime(timestamp, '%H:%M:%S').time(),
                                tzinfo=pytz.timezone('US/Pacific'))

    def _send_request(self, url: str, body: dict) -> Response:
        """Private helper function to make HTTP POST requests"""
        self.logger.info(f'sending request to {MY_TURN_URL}{url} with body - {body}')
        response = self.session.post(url=url, json=body)
        self.logger.info(f'got response from /{url} - {response.__dict__}')
        return response