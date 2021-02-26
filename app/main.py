#!/usr/bin/env python3
import logging
import os
import sys

import myTurnCABot

TOKEN_ENV_VAR = 'DISCORD_BOT_TOKEN'

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    try:
        myTurnCABot.run(os.environ[TOKEN_ENV_VAR])
    except KeyError:
        logging.error(f'Error: {TOKEN_ENV_VAR} is a required environment variable')
        sys.exit(1)
