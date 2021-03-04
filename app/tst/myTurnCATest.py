from datetime import date, datetime, timedelta
from unittest import TestCase
from unittest.mock import MagicMock, patch

import responses

from .constants import MOCK_VACCINE_DATA, EMPTY_LOCATIONS_RESPONSE, NON_EMPTY_LOCATION_RESPONSE, \
    EMPTY_LOCATION_AVAILABILITY_RESPONSE, UNAVAILABLE_LOCATION_AVAILABILITY_RESPONSE, \
    MIXED_LOCATION_AVAILABILITY_RESPONSE, TEST_LOCATION, EMPTY_AVAILABILITY_SLOTS_RESPONSE, \
    OLD_AVAILABILITY_SLOTS_RESPONSE, MIXED_AVAILABILITY_SLOTS_RESPONSE, AVAILABLE_LOCATION_AVAILABILITY_RESPONSE, \
    NEW_AVAILABILITY_SLOTS_RESPONSE
from ..src.constants import MY_TURN_URL
from ..src.myTurnCA import MyTurnCA, Location, LocationAvailability, LocationAvailabilitySlots


class MyTurnCATest(TestCase):
    @patch('app.src.myTurnCA.MyTurnCA._get_vaccine_data', MagicMock(return_value=MOCK_VACCINE_DATA))
    def setUp(self):
        self.my_turn_ca = MyTurnCA()

    def test_sanity(self):
        self.assertEqual(self.my_turn_ca.vaccine_data, MOCK_VACCINE_DATA)

    @responses.activate
    def test_no_locations(self):
        responses.add(method=responses.POST, url=f'{MY_TURN_URL}/locations/search', json=EMPTY_LOCATIONS_RESPONSE)
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
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}/locations/{TEST_LOCATION.location_id}/availability',
                      json=EMPTY_LOCATION_AVAILABILITY_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_availability(TEST_LOCATION, date.today(), date.today()),
                         LocationAvailability(location=TEST_LOCATION, dates_available=[]))

    @responses.activate
    def test_no_availability_given_only_unavailable_dates(self):
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}/locations/{TEST_LOCATION.location_id}/availability',
                      json=UNAVAILABLE_LOCATION_AVAILABILITY_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_availability(TEST_LOCATION, date.today(), date.today()),
                         LocationAvailability(location=TEST_LOCATION, dates_available=[]))

    @responses.activate
    def test_availability_given_mixed_dates(self):
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}/locations/{TEST_LOCATION.location_id}/availability',
                      json=MIXED_LOCATION_AVAILABILITY_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_availability(TEST_LOCATION, date.today(), date.today()),
                         LocationAvailability(location=TEST_LOCATION, dates_available=[
                             LocationAvailability.Availability(date_available=datetime.strptime(x['date'], '%Y-%m-%d').date(),
                                                               available=x['available'])
                             for x in MIXED_LOCATION_AVAILABILITY_RESPONSE['availability'] if x['available']]))

    @responses.activate
    def test_slots_given_no_availability(self):
        today = date.today()
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}/locations/{TEST_LOCATION.location_id}/date/{today.strftime("%Y-%m-%d")}/slots',
                      json=EMPTY_AVAILABILITY_SLOTS_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_slots(TEST_LOCATION, today),
                         LocationAvailabilitySlots(location=TEST_LOCATION, slots=[]))

    @responses.activate
    def test_slots_given_old_slots(self):
        today = date.today()
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}/locations/{TEST_LOCATION.location_id}/date/{today.strftime("%Y-%m-%d")}/slots',
                      json=OLD_AVAILABILITY_SLOTS_RESPONSE)
        self.assertEqual(self.my_turn_ca.get_slots(TEST_LOCATION, today),
                         LocationAvailabilitySlots(location=TEST_LOCATION, slots=[]))

    @responses.activate
    def test_slots_given_mixed_slots(self):
        today = date.today()
        responses.add(method=responses.POST,
                      url=f'{MY_TURN_URL}/locations/{TEST_LOCATION.location_id}/date/{today.strftime("%Y-%m-%d")}/slots',
                      json=MIXED_AVAILABILITY_SLOTS_RESPONSE)
        response = self.my_turn_ca.get_slots(TEST_LOCATION, today)
        self.assertEqual(response.location, TEST_LOCATION)
        self.assertEqual(len(response.slots), 1)

    @patch('app.src.myTurnCA.MyTurnCA.get_locations', MagicMock(return_value=[]))
    def test_appointments_given_no_locations(self):
        self.assertEqual(self.my_turn_ca.get_appointments(1, 2, date.today(), date.today()), [])

    @patch('app.src.myTurnCA.MyTurnCA.get_locations', MagicMock(return_value=[TEST_LOCATION]))
    def test_appointments_given_reversed_dates(self):
        with self.assertRaises(ValueError):
            self.my_turn_ca.get_appointments(1, 2, date.today() + timedelta(weeks=1), date.today())

    @patch('app.src.myTurnCA.MyTurnCA.get_locations', MagicMock(return_value=[TEST_LOCATION]))
    @patch('app.src.myTurnCA.MyTurnCA.get_availability',
           MagicMock(return_value=LocationAvailability(location=TEST_LOCATION, dates_available=[])))
    def test_appointments_given_no_availability(self):
        self.assertEqual(self.my_turn_ca.get_appointments(1, 2, date.today(), date.today()), [])

    @patch('app.src.myTurnCA.MyTurnCA.get_locations', MagicMock(return_value=[TEST_LOCATION]))
    @patch('app.src.myTurnCA.MyTurnCA.get_availability',
           MagicMock(return_value=LocationAvailability(location=TEST_LOCATION,
                                                       dates_available=[
                                                           LocationAvailability.Availability(date_available=datetime.strptime(x['date'], '%Y-%m-%d').date(),
                                                                                             available=x['available'])
                                                           for x in AVAILABLE_LOCATION_AVAILABILITY_RESPONSE['availability']])))
    @patch('app.src.myTurnCA.MyTurnCA.get_slots', MagicMock(return_value=LocationAvailabilitySlots(location=TEST_LOCATION, slots=[])))
    def test_appointments_give_availability_and_no_slots(self):
        self.assertEqual(self.my_turn_ca.get_appointments(1, 2, date.today(), date.today()), [])

    @patch('app.src.myTurnCA.MyTurnCA.get_locations', MagicMock(return_value=[TEST_LOCATION, TEST_LOCATION]))
    @patch('app.src.myTurnCA.MyTurnCA.get_availability')
    @patch('app.src.myTurnCA.MyTurnCA.get_slots')
    def test_appointments_give_availability_and_no_slots(self, get_slots, get_availability):
        availability = LocationAvailability(location=TEST_LOCATION,
                                            dates_available=[
                                                LocationAvailability.Availability(date_available=datetime.strptime(x['date'], '%Y-%m-%d').date(),
                                                                                  available=x['available'])
                                                for x in AVAILABLE_LOCATION_AVAILABILITY_RESPONSE['availability']])
        slots = LocationAvailabilitySlots(location=TEST_LOCATION,
                                          slots=[LocationAvailabilitySlots.AvailabilitySlots(local_start_time=datetime.strptime(x['localStartTime'], '%H:%M:%S'),
                                                                                             duration_seconds=x['durationSeconds']) for x in NEW_AVAILABILITY_SLOTS_RESPONSE['slotsWithAvailability']])
        get_availability.side_effect = [availability, availability]
        get_slots.side_effect = [slots, LocationAvailabilitySlots(location=TEST_LOCATION, slots=[])]
        self.assertEqual(self.my_turn_ca.get_appointments(1, 2, date.today(), date.today()), [slots])