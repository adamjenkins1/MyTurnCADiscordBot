# MyTurnCA constants
MY_TURN_URL = 'https://api.myturn.ca.gov/public'
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

# env var constants
DISCORD_BOT_TOKEN = 'DISCORD_BOT_TOKEN'
MONGO_USER = 'MONGO_USER'
MONGO_PASSWORD = 'MONGO_PASSWORD'
MONGO_HOST = 'MONGO_HOST'
MONGO_PORT = 'MONGO_PORT'

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