import functools
import json
import logging
import operator
from datetime import date, datetime
from typing import List

import pytz
import requests
from requests.adapters import HTTPAdapter

from .constants import MY_TURN_URL, ELIGIBLE_REQUEST_BODY, REQUESTS_MAX_RETRIES


class Location:
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
    class Availability:
        def __init__(self, date_available: date, available: bool):
            self.date = date_available
            self.available = available

        def __eq__(self, other):
            return self.date == other.date and self.available == other.available

    def __eq__(self, other):
        return self.location == other.location and self.dates_available == other.dates_available

    def __init__(self, location: Location, dates_available: List[Availability]):
        self.location = location
        self.dates_available = dates_available


class LocationAvailabilitySlots:
    class AvailabilitySlots:
        def __init__(self, local_start_time: datetime, duration_seconds: int):
            self.local_start_time = local_start_time
            self.duration_seconds = duration_seconds

        def __eq__(self, other):
            return self.local_start_time == other.local_start_time and self.duration_seconds == other.duration_seconds

    def __init__(self, location: Location, slots: List[AvailabilitySlots]):
        self.location = location
        self.slots = slots

    def __eq__(self, other):
        return self.location == other.location and self.slots == other.slots


class MyTurnCA:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.mount('https://', HTTPAdapter(max_retries=REQUESTS_MAX_RETRIES))
        self.vaccine_data = self._get_vaccine_data()

    def _get_vaccine_data(self) -> str:
        self.logger.info(f'sending request to {MY_TURN_URL}/eligibility with body - {json.dumps(ELIGIBLE_REQUEST_BODY)}')
        response = self.session.post(url=f'{MY_TURN_URL}/eligibility', json=ELIGIBLE_REQUEST_BODY).json()
        self.logger.info(f'got response from /eligibility - {json.dumps(response)}')

        if response['eligible'] is False:
            raise RuntimeError('something is wrong, default /eligibility body returned \'eligible\' = False')

        return response['vaccineData']

    def get_locations(self, latitude: float, longitude: float) -> List[Location]:
        body = {
            'location': {
                'lat': latitude,
                'lng': longitude
            },
            'fromDate': date.today().strftime('%Y-%m-%d'),
            'vaccineData': self.vaccine_data
        }

        self.logger.info(f'sending request to {MY_TURN_URL}/locations/search with body - {json.dumps(body)}')
        response = self.session.post(url=f'{MY_TURN_URL}/locations/search', json=body).json()
        self.logger.info(f'got response from /locations/search - {json.dumps(response)}')

        return [Location(location_id=x['extId'], name=x['name'], address=x['displayAddress'], booking_type=x['type'],
                         vaccine_data=x['vaccineData'], distance=x['distanceInMeters'])
                for x in response['locations']]

    def get_availability(self, location: Location, start_date: date, end_date: date) -> LocationAvailability:
        body = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'vaccineData': location.vaccine_data,
            'doseNumber': 1
        }

        self.logger.info(
            f'sending request to {MY_TURN_URL}/locations/{location.location_id}/availability with body - {json.dumps(body)}')
        response = self.session.post(url=f'{MY_TURN_URL}/locations/{location.location_id}/availability', json=body).json()
        self.logger.info(f'got response from /locations/{location.location_id}/availability - {json.dumps(response)}')
        return LocationAvailability(location=location,
                                    dates_available=[LocationAvailability.Availability(date_available=datetime.strptime(x['date'], '%Y-%m-%d').date(),
                                                                                       available=x['available'])
                                                     for x in response['availability'] if x['available'] is True])

    def get_slots(self, location: Location, start_date: date) -> LocationAvailabilitySlots:
        body = {
            'vaccineData': location.vaccine_data
        }

        self.logger.info(f'sending request to '
                         f'{MY_TURN_URL}/locations/{location.location_id}/date/{start_date.strftime("%Y-%m-%d")}/slots '
                         f'with body - {json.dumps(body)}')
        response = self.session.post(url=f'{MY_TURN_URL}/locations/{location.location_id}/date/{start_date.strftime("%Y-%m-%d")}/slots',
                                     json=body).json()
        self.logger.info(f'got response from /locations/{location.location_id}/date/{start_date.strftime("%Y-%m-%d")} - {json.dumps(response)}')

        return LocationAvailabilitySlots(location=location,
                                         slots=[LocationAvailabilitySlots.AvailabilitySlots(
                                             duration_seconds=x['durationSeconds'],
                                             local_start_time=self._combine_date_and_time(start_date, x['localStartTime']))
                                             for x in response['slotsWithAvailability']
                                             if self._combine_date_and_time(start_date, x['localStartTime']) > datetime.now(tz=pytz.timezone('US/Pacific'))])

    def get_appointments(self, latitude: float, longitude: float, start_date: date, end_date: date) -> List[LocationAvailabilitySlots]:
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
                                     [self.get_slots(location=location, start_date=day_available.date) for day_available in days_available]
                                     if location_appointment.slots]
            if not location_appointments:
                continue

            appointments.append(LocationAvailabilitySlots(location=location_appointments[0].location,
                                                          slots=functools.reduce(operator.add,
                                                                                 [location_appointment.slots for location_appointment in location_appointments])))

        return appointments

    @staticmethod
    def _combine_date_and_time(start_date: date, timestamp: str) -> datetime:
        return datetime.combine(start_date, datetime.strptime(timestamp, '%H:%M:%S').time(),
                                tzinfo=pytz.timezone('US/Pacific'))