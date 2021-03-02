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
NON_EMPTY_LOCATION_RESPONSE = {'locations': [LOCATION_DICT for i in range(0, 3)]}
EMPTY_LOCATION_AVAILABILITY_RESPONSE = {'availability': []}
UNAVAILABLE_LOCATION_AVAILABILITY_RESPONSE = {'availability': [{'date': '2025-01-01', 'available': False}]}
