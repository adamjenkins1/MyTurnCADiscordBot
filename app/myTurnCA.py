import json
import logging
from datetime import date

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


class MyTurnCA:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.vaccine_data = self._get_vaccine_data()

    def _get_vaccine_data(self):
        self.logger.debug(f'sending request to {URL}/eligibility with body - {json.dumps(ELIGIBLE_REQUEST_BODY)}')
        response = requests.post(url=f'{URL}/eligibility', json=ELIGIBLE_REQUEST_BODY).json()
        self.logger.debug(f'got response from /eligibility - {json.dumps(response)}')

        if response['eligible'] is False:
            raise RuntimeError('something is wrong, default /eligibility body returned \'eligible\' = False')

        return response['vaccineData']

    def get_locations(self, latitude: float, longitude: float):
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

        return response['locations']
