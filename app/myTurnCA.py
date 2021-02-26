import json
import logging
from datetime import date, datetime
from typing import List
import pytz

import requests

URL = 'https://api.myturn.ca.gov/public'
ELIGIBLE_REQUEST_BODY = {
    'eligibilityQuestionResponse': [
        {
            'id': 'q.screening.18.yr.of.age',
            'value': [
                'q.screening.18.yr.of.age'
            ],
            'type': 'multi-select'
        },
        {
            'id': 'q.screening.health.data',
            'value': [
                'q.screening.health.data'
            ],
            'type': 'multi-select'
        },
        {
            'id': 'q.screening.privacy.statement',
            'value': [
                'q.screening.privacy.statement'
            ],
            'type': 'multi-select'
        },
        {
            'id': 'q.screening.eligibility.age.range',
            'value': '75 and older',
            'type': 'single-select'
        },
        {
            'id': 'q.screening.eligibility.industry',
            'value': 'Other',
            'type': 'single-select'
        },
        {
            'id': 'q.screening.eligibility.county',
            'value': 'Alameda',
            'type': 'single-select'
        }
    ]
}


class Location:
    def __init__(self, location_id: str, name: str, booking_type: str, vaccine_data: str, distance: float):
        self.location_id = location_id
        self.name = name
        self.booking_type = booking_type
        self.vaccine_data = vaccine_data
        self.distance_in_meters = distance

    def __str__(self):
        return f'{self.name} ({self.location_id}) {self.distance_in_meters * 0.000621:.2f} mile(s) away'


class LocationAvailability:
    class Availability:
        def __init__(self, date_available: date, available: bool):
            self.date = date_available
            self.available = available

    def __init__(self, location_id: str, vaccine_data: str, dates_available: List[Availability]):
        self.location_id = location_id
        self.vaccine_data = vaccine_data
        self.dates_available = dates_available

    def __str__(self):
        return f'location_id:{self.location_id}, vaccine_data:{self.vaccine_data}, ' \
               f'dates_available:{[x.__dict__ for x in self.dates_available]}'


class LocationAvailabilitySlots:
    class AvailabilitySlots:
        def __init__(self, local_start_time: datetime, duration_seconds: int):
            self.local_start_time = local_start_time
            self.duration_seconds = duration_seconds

    def __init__(self, location_id: str, vaccine_data: str, slots: List[AvailabilitySlots]):
        self.location_id = location_id
        self.vaccine_data = vaccine_data
        self.slots = slots


class MyTurnCA:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.vaccine_data = self._get_vaccine_data()

    def _get_vaccine_data(self) -> str:
        self.logger.debug(f'sending request to {URL}/eligibility with body - {json.dumps(ELIGIBLE_REQUEST_BODY)}')
        response = requests.post(url=f'{URL}/eligibility', json=ELIGIBLE_REQUEST_BODY).json()
        self.logger.debug(f'got response from /eligibility - {json.dumps(response)}')

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

        self.logger.debug(f'sending request to {URL}/locations/search with body - {json.dumps(body)}')
        response = requests.post(url=f'{URL}/locations/search', json=body).json()
        self.logger.debug(f'got response from /locations/search - {json.dumps(response)}')

        return [Location(location_id=x['extId'], name=x['name'], booking_type=x['type'],
                         vaccine_data=x['vaccineData'], distance=x['distanceInMeters'])
                for x in response['locations']]

    def get_availability(self, location_id: str, start_date: date, end_date: date,
                         vaccine_data: str) -> LocationAvailability:
        body = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'vaccineData': vaccine_data,
            'doseNumber': 1
        }

        self.logger.debug(
            f'sending request to {URL}/locations/{location_id}/availability with body - {json.dumps(body)}')
        response = requests.post(url=f'{URL}/locations/{location_id}/availability', json=body)
        self.logger.debug(f'got response from /locations/{location_id}/availability - {json.dumps(response.json())}')

        if response.status_code != requests.codes.OK:
            raise ValueError(f'Something went wrong, location {location_id} probably doesn\'t exist')

        response_json = response.json()
        return LocationAvailability(location_id=response_json['locationExtId'],
                                    vaccine_data=response_json['vaccineData'],
                                    dates_available=[LocationAvailability.Availability(date_available=datetime.strptime(x['date'], "%Y-%m-%d").date(),
                                                                                       available=x['available'])
                                                     for x in response_json['availability'] if x['available'] is True])

    def get_slots(self, location_id: str, start_date: date, vaccine_data: str) -> LocationAvailabilitySlots:
        body = {
            'vaccineData': vaccine_data
        }

        self.logger.debug(f'sending request to '
                          f'{URL}/locations/{location_id}/date/{start_date.strftime("%Y-%m-%d")}/slots '
                          f'with body - {json.dumps(body)}')
        response = requests.post(url=f'{URL}/locations/{location_id}/date/{start_date.strftime("%Y-%m-%d")}/slots',
                                 json=body).json()
        self.logger.debug(f'got response from /locations/{location_id}/date/{start_date.strftime("%Y-%m-%d")} - {json.dumps(response)}')

        return LocationAvailabilitySlots(location_id=location_id, vaccine_data=response['vaccineData'],
                                         slots=[LocationAvailabilitySlots.AvailabilitySlots(
                                             duration_seconds=x['durationSeconds'],
                                             local_start_time=self._combine_date_and_time(start_date, x['localStartTime']))
                                             for x in response['slotsWithAvailability']
                                             if self._combine_date_and_time(start_date, x['localStartTime']) > datetime.now(tz=pytz.timezone('US/Pacific'))])

    @staticmethod
    def _combine_date_and_time(start_date: date, timestamp: str) -> datetime:
        return datetime.combine(start_date, datetime.strptime(timestamp, '%H:%M:%S').time(),
                                tzinfo=pytz.timezone('US/Pacific'))