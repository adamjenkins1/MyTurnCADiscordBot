from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock, patch

import responses

from .constants import MOCK_VACCINE_DATA, EMPTY_LOCATIONS_RESPONSE, NON_EMPTY_LOCATION_RESPONSE, \
    EMPTY_LOCATION_AVAILABILITY_RESPONSE, UNAVAILABLE_LOCATION_AVAILABILITY_RESPONSE
from ..src.constants import MY_TURN_URL
from ..src.myTurnCA import MyTurnCA, Location, LocationAvailability


class MyTurnCATest(TestCase):
    @patch('app.src.myTurnCA.MyTurnCA._get_vaccine_data', MagicMock(return_value=MOCK_VACCINE_DATA))
    def setUp(self):
        self.my_turn_ca = MyTurnCA()

    def test_sanity(self):
        self.assertEqual(self.my_turn_ca.vaccine_data, MOCK_VACCINE_DATA)

    @responses.activate
    def test_no_locations(self):
        responses.add(responses.POST, f'{MY_TURN_URL}/locations/search', json=EMPTY_LOCATIONS_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_locations(1, 2), [])

    @responses.activate
    def test_locations_found(self):
        responses.add(responses.POST, f'{MY_TURN_URL}/locations/search', json=NON_EMPTY_LOCATION_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_locations(1, 2),
                         [Location(location_id=location['extId'],
                                   name=location['name'],
                                   address=location['displayAddress'],
                                   vaccine_data=location['vaccineData'],
                                   distance=location['distanceInMeters'],
                                   booking_type=location['type'])
                          for location in NON_EMPTY_LOCATION_RESPONSE['locations']])

    @responses.activate
    def test_no_availability(self):
        responses.add(responses.POST, f'{MY_TURN_URL}/locations/search', json=NON_EMPTY_LOCATION_RESPONSE)
        location = self.my_turn_ca.get_locations(1, 2)[0]
        responses.add(responses.POST,
                      f'{MY_TURN_URL}/locations/{location.location_id}/availability',
                      json=EMPTY_LOCATION_AVAILABILITY_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_availability(location, date.today(), date.today()),
                         LocationAvailability(location=location, dates_available=[]))

    @responses.activate
    def test_no_availability_given_only_unavailable_dates(self):
        responses.add(responses.POST, f'{MY_TURN_URL}/locations/search', json=NON_EMPTY_LOCATION_RESPONSE)
        location = self.my_turn_ca.get_locations(1, 2)[0]
        responses.add(responses.POST,
                      f'{MY_TURN_URL}/locations/{location.location_id}/availability',
                      json=UNAVAILABLE_LOCATION_AVAILABILITY_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_availability(location, date.today(), date.today()),
                         LocationAvailability(location=location, dates_available=[]))
