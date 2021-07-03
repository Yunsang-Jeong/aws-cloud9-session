import sys
import uuid
import copy
import pathlib
import logging

from __init__ import Manager
from __init__ import save_dict_as_json, load_json_as_dict

try:
    import boto3
    import botocore
except ModuleNotFoundError:
    print('boto3, botocore is not installed')
    sys.exit(1)

try:
    from PyInquirer import prompt
except ModuleNotFoundError:
    print('PyInquirer is not installed')
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
# Configuration
BASE_PATH = pathlib.Path(__file__).parent.resolve()

CONFIG_DIR = f'{BASE_PATH}/configuration/'
CONFIG_NAME = 'configuration.json'

PROVISIOND_DIR = f'{BASE_PATH}/configuration/'
PROVISIOND_NAME = 'provisioned.json'
########################################

PYUI_QUESTSION = [{
    'type': 'list',
    'name': 'jobs',
    'message': 'Which job do you want?',
    'choices': ['Prepare session', 'Clear session']
}]

class Cloud9Manager(Manager):
    def __init__(self):
        super().__init__()

    def __del__(self):
        pass

    def _validate(self):
        # validate configuration
        if not pathlib.Path(CONFIG_DIR+CONFIG_NAME).exists():
            return False

        self.conf = self._load_configuration(CONFIG_DIR, CONFIG_NAME)

        # validate provisioned.json
        if not pathlib.Path(PROVISIOND_DIR+PROVISIOND_NAME).exists():
            save_dict_as_json('w', PROVISIOND_DIR, PROVISIOND_NAME, {
                'iam_group': {},
                'iam_user_teacher': {},
                'iam_user_student': {},
                'cloud9_project': {}
            })

        return True

    def _get_environment_id_by_name(self, project_name):
        try:
            resp = self.cli.list_environments()
        except:
            LOGGER.error('Error to get list of enviroments', exc_info=True)
            return False

        try:
            resp = self.cli.describe_environments(environmentIds=resp['environmentIds'])
        except:
            LOGGER.error('Error to describe enviroments', exc_info=True)
            return False

        for env in resp['environments']:
            if env['name'] == project_name:
                LOGGER.debug(f'Success to get environment id of {project_name}', exc_info=True)
                return env['id']
        
        return False

    def _create_project(self, owner_user_arn):
        user_name = owner_user_arn.split('/')[1]
        project_name = self.conf['cloud9_project']['project_name_fmt'].format(user_name)
        try:
            resp = self.cli.create_environment_ec2(
                name=project_name,
                description=f'AWS Cloud9 for coding class',
                instanceType=self.conf['cloud9_project']['instance_type'],
                ownerArn=owner_user_arn,
                connectionType='CONNECT_SSH'
            )
        except self.cli.exceptions.ConflictException:
            LOGGER.error(f'{project_name} is already used.')
            return (project_name, self._get_environment_id_by_name(project_name))
        except botocore.exceptions.ClientError as e:
            LOGGER.error(f'Error to create a project({project_name})\n{e}')
            return (False, False)

        if environment_id := resp.get('environmentId', False):
            LOGGER.debug(f'Success to create a project({project_name})')
            return (project_name, environment_id)
        else:
            return (False, False)

    def _destroy_project(self, environment_id):
        try:
            resp = self.cli.delete_environment(environmentId = environment_id)
            LOGGER.debug(f'Success to destory a project({environment_id})')
            return True
        except self.cli.exceptions.NotFoundException:
            LOGGER.error(f'{environment_id} is already destroyed.')
            return True
        except:
            LOGGER.error(f'Error to destory a project({environment_id})', exc_info=True)
            return False

    def _share_project(self, environment_id, target_user_arn):
        try:
            resp = self.cli.create_environment_membership(
                environmentId=environment_id,
                userArn=target_user_arn,
                permissions='read-write'
            )
            LOGGER.debug(f'Success to share project ({environment_id}, {target_user_arn})')
            return True
        except:
            LOGGER.error(f'Error to share proejct ({environment_id}, {target_user_arn})', exc_info=True)
            return False

    def _prepare_session(self):
        provisioned = load_json_as_dict(PROVISIOND_DIR, PROVISIOND_NAME)
        try:
            # 1. Create Cloud9 proejct for teacher
            for name, arn in provisioned['iam_user_teacher'].items():
                project_name, environment_id = self._create_project(arn)
                if project_name and environment_id:
                    provisioned['cloud9_project'].update({
                        name: {'project_name': project_name, 'environment_id': environment_id, 'owner_type': 'teacher'}
                    })

            # 2. Create Cloud9 proejct for student
            for name, arn in provisioned['iam_user_student'].items():
                project_name, environment_id = self._create_project(arn)
                if project_name and environment_id:
                    provisioned['cloud9_project'].update({
                        name: {'project_name': project_name, 'environment_id': environment_id, 'owner_type': 'student'}
                    })

            # 3. Share Cloud9 project with teacher
            for name, arn in provisioned['iam_user_teacher'].items():
                for _, detail in provisioned['cloud9_project'].items():
                    if detail['owner_type'] == 'student':
                        self._share_project(detail['environment_id'], arn)
        finally:
            save_dict_as_json('w', PROVISIOND_DIR, PROVISIOND_NAME, provisioned)

    def _clear_session(self):
        provisioned = load_json_as_dict(PROVISIOND_DIR, PROVISIOND_NAME)
        try:
            for name, detail in provisioned['cloud9_project'].items():
                if self._destroy_project(detail['environment_id']):
                    provisioned['cloud9_project'][name] = {}
            provisioned['cloud9_project'] = { name: detail for name, detail in provisioned['cloud9_project'].items() if detail != {} }
        finally:
            save_dict_as_json('w', f'{BASE_PATH}/configuration', 'provisioned.json', provisioned)

    def run(self):
        if not self._validate():
            LOGGER.error(f'Fail to get configuration file')
            return False

        self.cli = self.session.client('cloud9', config=self.cli_config)

        if resp := prompt(PYUI_QUESTSION):
            if resp['jobs'] == 'Prepare session':
                self._prepare_session()
            elif resp['jobs'] == 'Clear session':
                self._clear_session()
            else:
                return False
        else:
            return False

        return True


if __name__ == '__main__':
    obj = Cloud9Manager()
    obj.run()