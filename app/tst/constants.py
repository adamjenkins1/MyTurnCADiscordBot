"""Test constants module"""
from ..src.myTurnCA import Location

TEST_API_KEY = 'TEST_API_KEY'
BAD_JSON_RESPONSE = 'this is not a json!'
MOCK_VACCINE_DATA = 'VACCINE_DATA'
EMPTY_LOCATIONS_RESPONSE = {'locations': []}
LOCATION_DICT = {
    'extId': 'EXT_ID',
    'name': 'NAME',
    'displayAddress': 'DISPLAY_ADDRESS',
    'type': 'TYPE',
    'vaccineData': 'VACCINE_DATA',
    'distanceInMeters': 1.2
}
TEST_LOCATION = Location(location_id=LOCATION_DICT['extId'],
                         name=LOCATION_DICT['name'],
                         booking_type=LOCATION_DICT['type'],
                         address=LOCATION_DICT['displayAddress'],
                         vaccine_data=LOCATION_DICT['vaccineData'],
                         distance=LOCATION_DICT['distanceInMeters'])
NON_EMPTY_LOCATION_RESPONSE = {'locations': [LOCATION_DICT for i in range(0, 3)]}
EMPTY_LOCATION_AVAILABILITY_RESPONSE = {'availability': []}
UNAVAILABLE_LOCATION_AVAILABILITY_RESPONSE = {'availability': [{'date': '2025-01-01', 'available': False}]}
MIXED_LOCATION_AVAILABILITY_RESPONSE = {
    'availability': [
        {'date': '2025-01-01', 'available': False},
        {'date': '2025-02-01', 'available': True}
    ]
}
AVAILABLE_LOCATION_AVAILABILITY_RESPONSE = {
    'availability': [
        {'date': '2025-02-01', 'available': True}
    ]
}
EMPTY_AVAILABILITY_SLOTS_RESPONSE = {'slotsWithAvailability': []}
NEW_SLOT_TIME = '10:00:00'
OLD_SLOT_TIME = '8:00:00'
CURRENT_TIME = '9:00:00'
OLD_AVAILABILITY_SLOTS_RESPONSE = {
    'slotsWithAvailability': [
        {
            'durationSeconds': 300,
            'localStartTime': OLD_SLOT_TIME
        }
    ]
}
NEW_AVAILABILITY_SLOTS_RESPONSE = {
    'slotsWithAvailability': [
        {
            'durationSeconds': 300,
            'localStartTime': NEW_SLOT_TIME
        }
    ]
}
MIXED_AVAILABILITY_SLOTS_RESPONSE = {
    'slotsWithAvailability': [
        {
            'durationSeconds': 300,
            'localStartTime': OLD_SLOT_TIME
        },
        {
            'durationSeconds': 300,
            'localStartTime': NEW_SLOT_TIME
        }
    ]
}
