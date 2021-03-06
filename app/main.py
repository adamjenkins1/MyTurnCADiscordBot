#!/usr/bin/env python3
"""Main driver for MyTurnBot"""
import logging
import os
import sys

from src import myTurnCABot
from src.constants import DISCORD_BOT_TOKEN, MONGO_USER, MONGO_PASSWORD, MONGO_HOST, MONGO_PORT

ENV_VARS = {
    DISCORD_BOT_TOKEN: '',
    MONGO_USER: '',
    MONGO_PASSWORD: '',
    MONGO_HOST: '',
    MONGO_PORT: ''
}


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    for var in ENV_VARS:
        try:
            ENV_VARS[var] = os.environ[var]
        except KeyError:
            logging.error(f'Error: {var} is a required environment variable')
            sys.exit(1)

    myTurnCABot.run(token=ENV_VARS[DISCORD_BOT_TOKEN],
                    mongodb_user=ENV_VARS[MONGO_USER],
                    mongodb_password=ENV_VARS[MONGO_PASSWORD],
                    mongodb_host=ENV_VARS[MONGO_HOST],
                    mongodb_port=ENV_VARS[MONGO_PORT])