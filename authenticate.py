#!/usr/bin/python3

import os
from src.auth import GLAuth
from src.logger import log
from dotenv import load_dotenv
from pathlib import Path

dotenv_path = Path(__file__).parent.joinpath('.env')
if not dotenv_path.is_file():
    raise Exception('Please create a .env with the required configuration')

load_dotenv(dotenv_path=dotenv_path)

envfile = os.getenv('GL_ENV_FILE', '.env')
recording_path = os.getenv('BBB_RECORDING_PATH', '/var/bigbluebutton/published/presentation')

if not Path(envfile).is_file():
    raise Exception('Greenlight env file not found')

if not Path(recording_path).is_dir():
    raise Exception('BigBlueButton recordings directory not found')

glauth = GLAuth(envfile, recording_path)
glauth.do_auth()
exit(0)
