#!/usr/bin/env python3
"""Main driver for MyTurnBot"""
import argparse
import logging
import os
import sys

from src import myTurnCABot
from src.constants import DISCORD_BOT_TOKEN, MONGO_USER, MONGO_PASSWORD, MONGO_HOST, MONGO_PORT, NAMESPACE
from src.notificationGenerator import NotificationGenerator

BOT_ENV_VARS = {
    DISCORD_BOT_TOKEN: '',
    MONGO_USER: '',
    MONGO_PASSWORD: '',
    MONGO_HOST: '',
    MONGO_PORT: '',
    NAMESPACE: ''
}

WORKER_ENV_VARS = {
    MONGO_USER: '',
    MONGO_PASSWORD: '',
    MONGO_HOST: '',
    MONGO_PORT: ''
}


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--channel_id', type=int)
    parser.add_argument('--user_id', type=int)
    parser.add_argument('--zip_code', type=int)
    args = parser.parse_args()

    if args.worker:
        for var in WORKER_ENV_VARS:
            try:
                WORKER_ENV_VARS[var] = os.environ[var]
            except KeyError:
                logging.error(f'Error: {var} is a required environment variable')
                sys.exit(1)

        notification_generator = NotificationGenerator(mongodb_user=WORKER_ENV_VARS[MONGO_USER],
                                                       mongodb_password=WORKER_ENV_VARS[MONGO_PASSWORD],
                                                       mongodb_host=WORKER_ENV_VARS[MONGO_HOST],
                                                       mongodb_port=WORKER_ENV_VARS[MONGO_PORT])
        notification_generator.generate_notification(channel_id=args.channel_id,
                                                     user_id=args.user_id,
                                                     zip_code=args.zip_code)
        sys.exit(0)

    for var in BOT_ENV_VARS:
        try:
            BOT_ENV_VARS[var] = os.environ[var]
        except KeyError:
            logging.error(f'Error: {var} is a required environment variable')
            sys.exit(1)

    myTurnCABot.run(token=BOT_ENV_VARS[DISCORD_BOT_TOKEN],
                    namespace=BOT_ENV_VARS[NAMESPACE],
                    mongodb_user=BOT_ENV_VARS[MONGO_USER],
                    mongodb_password=BOT_ENV_VARS[MONGO_PASSWORD],
                    mongodb_host=BOT_ENV_VARS[MONGO_HOST],
                    mongodb_port=BOT_ENV_VARS[MONGO_PORT])