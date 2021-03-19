"""Unit tests for MyTurnCA API wrapper"""
from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import MagicMock, patch

import pytz
import responses

from .constants import MOCK_VACCINE_DATA, EMPTY_LOCATIONS_RESPONSE, NON_EMPTY_LOCATION_RESPONSE, \
    EMPTY_LOCATION_AVAILABILITY_RESPONSE, UNAVAILABLE_LOCATION_AVAILABILITY_RESPONSE, \
    MIXED_LOCATION_AVAILABILITY_RESPONSE, TEST_LOCATION, EMPTY_AVAILABILITY_SLOTS_RESPONSE, \
    OLD_AVAILABILITY_SLOTS_RESPONSE, MIXED_AVAILABILITY_SLOTS_RESPONSE, AVAILABLE_LOCATION_AVAILABILITY_RESPONSE, \
    NEW_AVAILABILITY_SLOTS_RESPONSE, BAD_JSON_RESPONSE, CURRENT_TIME
from ..src.constants import MY_TURN_URL, LOCATIONS_URL, LOCATION_AVAILABILITY_URL, LOCATION_AVAILABILITY_SLOTS_URL
from ..src.myTurnCA import MyTurnCA, Location, LocationAvailability, LocationAvailabilitySlots


class MyTurnCATest(TestCase):
    """Main unit test class"""
    @patch('app.src.myTurnCA.MyTurnCA._get_vaccine_data', MagicMock(return_value=MOCK_VACCINE_DATA))
    def setUp(self):
        self.my_turn_ca = MyTurnCA()
        self.today = datetime.now(tz=pytz.timezone('US/Pacific')).date()
        self.slots_url = LOCATION_AVAILABILITY_SLOTS_URL.format(location_id=TEST_LOCATION.location_id,
                                                                start_date=self.today.strftime('%Y-%m-%d'))

    def set_up_mock_datetime(self, mock: MagicMock):
        """Helper method to setup mock datetime behavior"""
        mock.now = MagicMock(return_value=datetime.combine(self.today,
                                                           datetime.strptime(CURRENT_TIME, '%H:%M:%S').time(),
                                                           tzinfo=pytz.timezone('US/Pacific')))
        mock.combine = datetime.combine
        mock.strptime = datetime.strptime

    def test_sanity(self):
        """Sanity test to make sure _get_vaccine_data was properly mocked"""
        self.assertEqual(self.my_turn_ca.vaccine_data, MOCK_VACCINE_DATA)

    @responses.activate
    def test_no_locations(self):
        """Tests that no locations are returned given empty response"""
        responses.add(method=responses.POST, url=f'{MY_TURN_URL}{LOCATIONS_URL}', json=EMPTY_LOCATIONS_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_locations(1, 2), [])

    @responses.activate
    def test_no_locations_on_decode_error(self):
        """Tests that no locations are returned given a non-JSON response"""
        responses.add(method=responses.POST, url=f'{MY_TURN_URL}{LOCATIONS_URL}', body=BAD_JSON_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_locations(1, 2), [])

    @responses.activate
    def test_locations_found(self):
        """Tests that locations are properly returned given non-empty response"""
        responses.add(responses.POST, f'{MY_TURN_URL}{LOCATIONS_URL}', json=NON_EMPTY_LOCATION_RESPONSE)
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
        """Tests that no dates are returned given empty response"""
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}{LOCATION_AVAILABILITY_URL.format(location_id=TEST_LOCATION.location_id)}',
                      json=EMPTY_LOCATION_AVAILABILITY_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_availability(TEST_LOCATION, self.today, self.today),
                         LocationAvailability(location=TEST_LOCATION, dates_available=[]))

    @responses.activate
    def test_no_availability_on_decode_error(self):
        """Tests that no dates are returned given a non-JSON response"""
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}{LOCATION_AVAILABILITY_URL.format(location_id=TEST_LOCATION.location_id)}',
                      body=BAD_JSON_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_availability(TEST_LOCATION, self.today, self.today),
                         LocationAvailability(location=TEST_LOCATION, dates_available=[]))

    @responses.activate
    def test_no_availability_given_only_unavailable_dates(self):
        """Tests that no dates are returned given only unavailable dates"""
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}{LOCATION_AVAILABILITY_URL.format(location_id=TEST_LOCATION.location_id)}',
                      json=UNAVAILABLE_LOCATION_AVAILABILITY_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_availability(TEST_LOCATION, self.today, self.today),
                         LocationAvailability(location=TEST_LOCATION, dates_available=[]))

    @responses.activate
    def test_availability_given_mixed_dates(self):
        """Tests that unavailable dates are properly filtered out and available dates are returned"""
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}{LOCATION_AVAILABILITY_URL.format(location_id=TEST_LOCATION.location_id)}',
                      json=MIXED_LOCATION_AVAILABILITY_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_availability(TEST_LOCATION, self.today, self.today),
                         LocationAvailability(location=TEST_LOCATION,
                                              dates_available=[datetime.strptime(x['date'], '%Y-%m-%d').date()
                                                               for x in MIXED_LOCATION_AVAILABILITY_RESPONSE['availability'] if x['available']]))

    @responses.activate
    def test_slots_given_no_availability(self):
        """Tests that no slots are returned given empty response"""
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}{self.slots_url}',
                      json=EMPTY_AVAILABILITY_SLOTS_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_slots(TEST_LOCATION, self.today),
                         LocationAvailabilitySlots(location=TEST_LOCATION, slots=[]))

    @responses.activate
    def test_slots_given_json_decode_error(self):
        """Tests that no slots are returned given a non-JSON response"""
        responses.add(method=responses.POST, url=f'{MY_TURN_URL}{self.slots_url}', body=BAD_JSON_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_slots(TEST_LOCATION, self.today),
                         LocationAvailabilitySlots(location=TEST_LOCATION, slots=[]))

    @responses.activate
    @patch('app.src.myTurnCA.datetime')
    def test_slots_given_old_slots(self, mock_datetime):
        """Tests that no slots are returned given slots that already occurred"""
        self.set_up_mock_datetime(mock_datetime)
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}{self.slots_url}',
                      json=OLD_AVAILABILITY_SLOTS_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_slots(TEST_LOCATION, self.today),
                         LocationAvailabilitySlots(location=TEST_LOCATION, slots=[]))

    @responses.activate
    @patch('app.src.myTurnCA.datetime')
    def test_slots_given_mixed_slots(self, mock_datetime):
        """Tests that upcoming slots are returned and old slots are filtered out"""
        self.set_up_mock_datetime(mock_datetime)
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}{self.slots_url}',
                      json=MIXED_AVAILABILITY_SLOTS_RESPONSE)
        response = self.my_turn_ca.get_slots(TEST_LOCATION, self.today)
        self.assertEqual(response.location, TEST_LOCATION)
        self.assertEqual(len(response.slots), 1)

    @patch('app.src.myTurnCA.MyTurnCA.get_locations', MagicMock(return_value=[]))
    def test_appointments_given_no_locations(self):
        """Tests that no slots are returned when no locations are found"""
        self.assertEqual(self.my_turn_ca.get_appointments(1, 2, self.today, self.today), [])

    @patch('app.src.myTurnCA.MyTurnCA.get_locations', MagicMock(return_value=[TEST_LOCATION]))
    def test_appointments_given_reversed_dates(self):
        """Tests that exception is thrown if the end_date comes before the start_date"""
        with self.assertRaises(ValueError):
            self.my_turn_ca.get_appointments(1, 2, self.today + timedelta(weeks=1), self.today)

    @patch('app.src.myTurnCA.MyTurnCA.get_locations', MagicMock(return_value=[TEST_LOCATION]))
    @patch('app.src.myTurnCA.MyTurnCA.get_availability',
           MagicMock(return_value=LocationAvailability(location=TEST_LOCATION, dates_available=[])))
    def test_appointments_given_no_availability(self):
        """Tests that no slots are returned if no locations have any availability"""
        self.assertEqual(self.my_turn_ca.get_appointments(1, 2, self.today, self.today), [])

    @patch('app.src.myTurnCA.MyTurnCA.get_locations', MagicMock(return_value=[TEST_LOCATION]))
    @patch('app.src.myTurnCA.MyTurnCA.get_availability',
           MagicMock(return_value=LocationAvailability(location=TEST_LOCATION,
                                                       dates_available=[datetime.strptime(x['date'], '%Y-%m-%d').date()
                                                                        for x in AVAILABLE_LOCATION_AVAILABILITY_RESPONSE['availability']])))
    @patch('app.src.myTurnCA.MyTurnCA.get_slots', MagicMock(return_value=LocationAvailabilitySlots(location=TEST_LOCATION, slots=[])))
    def test_appointments_given_availability_and_no_slots(self):
        """Tests that no slots are returned when a location has days available but no open slots"""
        self.assertEqual(self.my_turn_ca.get_appointments(1, 2, self.today, self.today), [])

    @patch('app.src.myTurnCA.MyTurnCA.get_locations', MagicMock(return_value=[TEST_LOCATION, TEST_LOCATION]))
    @patch('app.src.myTurnCA.MyTurnCA.get_availability')
    @patch('app.src.myTurnCA.MyTurnCA.get_slots')
    def test_appointments_given_availability_and_new_slots(self, get_slots, get_availability):
        """Tests that available slots are returned and locations without available slots are filtered out"""
        availability = LocationAvailability(location=TEST_LOCATION,
                                            dates_available=[datetime.strptime(x['date'], '%Y-%m-%d').date()
                                                             for x in AVAILABLE_LOCATION_AVAILABILITY_RESPONSE['availability']])
        slots = LocationAvailabilitySlots(location=TEST_LOCATION,
                                          slots=[datetime.strptime(x['localStartTime'], '%H:%M:%S')
                                                 for x in NEW_AVAILABILITY_SLOTS_RESPONSE['slotsWithAvailability']])
        get_availability.side_effect = [availability, availability]
        get_slots.side_effect = [slots, LocationAvailabilitySlots(location=TEST_LOCATION, slots=[])]
        self.assertEqual(self.my_turn_ca.get_appointments(1, 2, self.today, self.today), [slots])