import json
import pathlib
import logging

try:
    import boto3
    import botocore
except ModuleNotFoundError:
    print('boto3, botocore is not installed')
    sys.exit(1)

########################################
# Logging
LOGLEVEL = logging.DEBUG
LOGFORMAT = '└ %(asctime)s %(levelname)s on "%(filename)s", %(message)s'

loghandler = logging.StreamHandler()
loghandler.setLevel(LOGLEVEL)
loghandler.setFormatter(logging.Formatter(LOGFORMAT))

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(LOGLEVEL)
LOGGER.addHandler(loghandler)
########################################

########################################
# Output
BASE_PATH = pathlib.Path(__file__).parent.resolve()
########################################

def save_dict_as_json(mode, location, filename, data):
    try:
        pathlib.Path(location).mkdir(exist_ok=True)
        with open(f'{location}/{filename}', mode) as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except:
        LOGGER.error('Error to save a dictionary as a json', exc_info=True)
        return False

def load_json_as_dict(location, filename):
    if pathlib.Path(location).exists():
        with open(f'{location}/{filename}', 'r') as f:
            data = json.load(f)
        return data
    else:
        LOGGER.error('Error to save a dictionary as a json', exc_info=False)
        return {}


class Manager(object):
    def __init__(self):
        self.session = self._get_session_by_profile()
        self.cli_config = botocore.config.Config(
            retries = { 'max_attempts': 10, 'mode': 'adaptive' }
        )

    def __del__(self):
        pass

    def _get_session_by_profile(self, profile_name='default'):
        try:
            LOGGER.debug(f'boto3 version is {boto3.__version__}')
            return boto3.session.Session(profile_name=profile_name)
        except botocore.exceptions.ProfileNotFound as err:
            LOGGER.error('Error to get profile name', exc_info=True)
            return None

    def _load_configuration(self, location, filename):
        return load_json_as_dict(location, filename)