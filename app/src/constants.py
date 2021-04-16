from urllib3.util import Retry

"""Constants module"""
# MyTurnCA constants
REQUESTS_MAX_RETRIES = 100
MY_TURN_URL = 'https://api.myturn.ca.gov/public/'
DEFAULT_RETRY_STRATEGY = Retry(
    total=REQUESTS_MAX_RETRIES,
    backoff_factor=0.2,
    status_forcelist=[403, 429, 500, 502, 503, 504],
    allowed_methods=frozenset(['GET', 'POST']))
ELIGIBLE_REQUEST_BODY = {
    'eligibilityQuestionResponse': [
        {
            'id': 'q.screening.privacy.statement',
            'type': 'multi-select',
            'value': ['q.screening.privacy.statement']
        },
        {
            'id': 'q.screening.eligibility.age.range',
            'type': 'single-select',
            'value': '18 and older'
        },
        {
            'id': 'q.screening.eligibility.county',
            'type': 'single-select',
            'value': 'Alameda'
        },
        {
            'id': 'q.screening.different.county',
            'type': 'single-select',
            'value': 'No'
        },
        {
            'id': 'q.screening.county.of.work',
            'type': 'single-select'
        },
        {
            'id': 'q.screening.accessibility.code',
            'type': 'text'
        },
        {
            'id': 'q.screening.18.yr.of.age',
            'type': 'multi-select',
            'value': ['q.screening.18.yr.of.age']
        },
        {
            'id': 'q.screening.health.data',
            'type': 'multi-select',
            'value': ['q.screening.health.data']
        }
    ],
    'url': 'https://myturn.ca.gov/screening'
}
ELIGIBILITY_URL = 'eligibility'
LOCATIONS_URL = 'locations/search'
LOCATION_AVAILABILITY_URL = 'locations/{location_id}/availability'
LOCATION_AVAILABILITY_SLOTS_URL = 'locations/{location_id}/date/{start_date}/slots'
JSON_DECODE_ERROR_MSG = 'unable to deserialize response body, "{body}" must not be a JSON, returning empty response'
GOOD_BOT_HEADER = 'goodbot'
FIREFOX_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) Gecko/20100101 Firefox/86.0'
MY_TURN_ORIGIN = 'https://myturn.ca.gov'
REQUEST_HEADERS = {
    'user-agent': FIREFOX_USER_AGENT,
    'origin': MY_TURN_ORIGIN
}

# env var constants
DISCORD_BOT_TOKEN = 'DISCORD_BOT_TOKEN'
MONGO_USER = 'MONGO_USER'
MONGO_PASSWORD = 'MONGO_PASSWORD'
MONGO_HOST = 'MONGO_HOST'
MONGO_PORT = 'MONGO_PORT'
NAMESPACE = 'NAMESPACE'
JOB_IMAGE = 'JOB_IMAGE'
MY_TURN_API_KEY = 'MY_TURN_API_KEY'

# MyTurnCABot constants
COMMAND_PREFIX = '!'
BOT_DESCRIPTION = 'Bot to help you get a COVID-19 vaccination appointment in CA'
CANCEL_NOTIFICATION_BRIEF = 'Cancels notification request'
CANCEL_NOTIFICATION_DESCRIPTION = 'Cancels the notification request for a given zip code'
NOTIFY_BRIEF = 'Notifies you when appointments are available'
NOTIFY_DESCRIPTION = 'Notifies you when appointments become available within the next week near the given zip code'
GET_NOTIFICATIONS_DESCRIPTION = 'Lists active notification requests'
GET_LOCATIONS_DESCRIPTION = 'Lists vaccination locations near the given zip code'
GET_APPOINTMENTS_BRIEF = 'Lists appointments at nearby vaccination locations'
GET_APPOINTMENTS_DESCRIPTION = 'Lists how many appointments are available within the next week at vaccination ' \
                               'locations near the given zip code'
NOTIFICATION_WAIT_PERIOD = 30
JOB_MAX_RETRIES = 6
JOB_TTL_SECONDS_AFTER_FINISHED = 0
JOB_NAME_PREFIX = 'myturncabot-notification-job-'
JOB_RESTART_POLICY = 'OnFailure'
JOB_DELETION_PROPAGATION_POLICY = 'Foreground'
JOB_RESOURCE_REQUESTS = {'memory': '128Mi', 'cpu': '5m'}