import sys
import json
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

class IAMManager(Manager):
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

    def _get_user_arn(self, name):
        try:
            resp = self.cli.get_user(UserName=name)
            return resp['User']['Arn']
        except:
            LOGGER.error(f'Error to get arn of iam user ({name})', exc_info=True)
            return False

    def _create_iam_user(self, name, password, group):
        arn = ''
        try:
            resp = self.cli.create_user(UserName=name)
            arn = resp['User']['Arn']
        except self.cli.exceptions.EntityAlreadyExistsException as e:
            LOGGER.error(f'The iam user already exists. ({name})')
            return self._get_user_arn(name)
        except:
            LOGGER.error(f'Error to create iam user ({name})', exc_info=True)
            return False

        try:
            self.cli.create_login_profile(
                UserName=name,
                Password=password,
                PasswordResetRequired=False
            )
        except self.cli.exceptions.EntityAlreadyExistsException as e:
            LOGGER.error(f'The iam user already has login profile ({name})')
        except:
            LOGGER.error(f'Error to create login profile ({name})', exc_info=True)
            return False
        
        try:
            self.cli.add_user_to_group(
                UserName=name,
                GroupName=group
            )
        except:
            LOGGER.error(f'Error to add user to group ({name}, {group})', exc_info=True)
            return False

        LOGGER.debug(f'Success to create a iam user ({name})')
        return arn

    def _destroy_iam_user(self, name):
        try:
            resp = self.cli.list_groups_for_user(UserName=name)
            for g in resp['Groups']:    
                self.cli.remove_user_from_group(UserName=name, GroupName=g['GroupName'])
        except self.cli.exceptions.NoSuchEntityException as e:
            LOGGER.error(f'The iam user is already destroyed ({name})')
            return True

        except:
            LOGGER.error(f'Error to detach from iam group that the user belongs to ({name})', exc_info=True)
            return False

        try:
            self.cli.delete_login_profile(UserName=name)
        except:
            LOGGER.error(f'Error to delete login profile ({name})', exc_info=True)
            return False

        try:
            resp = self.cli.list_groups_for_user(UserName=name)
            self.cli.delete_user(UserName=name)
        except:
            LOGGER.error(f'Error to destroy iam user ({name})', exc_info=True)
            return False
        
        LOGGER.debug(f'Success to destroy a iam user ({name})')
        return True

    def _get_group_arn(self, name):
        try:
            resp = self.cli.get_group(GroupName=name)
            return resp['Group']['Arn']
        except:
            LOGGER.error(f'Error to get arn of iam group ({name})', exc_info=True)
            return False

    def _create_group(self, name, policy_list):
        arn = ''
        try:
            resp = self.cli.create_group(GroupName=name)
            arn = resp['Group']['Arn']
        except self.cli.exceptions.EntityAlreadyExistsException as e:
            LOGGER.error(f'The iam group already exists. ({name})')
            arn = self._get_group_arn(name)
        except:
            LOGGER.error(f'Error to create iam group ({name})', exc_info=True)
            return False

        try:
            for policy in policy_list:
                policy_dict = load_json_as_dict(f'{BASE_PATH}/policy', policy['filename'])
                resp = self.cli.put_group_policy(
                    GroupName=name,
                    PolicyName=policy['name'],
                    PolicyDocument=json.dumps(policy_dict)
                )
            LOGGER.debug(f'Success to create the iam group ({name})')

            return arn
        except:
            LOGGER.error(f'Error to create inline policy for iam group ({name})', exc_info=True)
            return False

    def _destroy_iam_group(self, name):       
        try:
            resp = self.cli.list_group_policies(GroupName=name)
            for policy_name in resp['PolicyNames']:
                self.cli.delete_group_policy(GroupName=name, PolicyName=policy_name)
        except self.cli.exceptions.NoSuchEntityException as e:
            LOGGER.error(f'The iam group is already destroyed ({name})')
            return True
        except:
            LOGGER.error(f'Error to detache inline policy from iam group ({name})', exc_info=True)
            return False

        try:
            self.cli.delete_group(GroupName=name)    
        except:
            LOGGER.error(f'Error to destroy iam group ({name})', exc_info=True)
            return False

        LOGGER.debug(f'Success to destroy the iam group ({name})')
        return True

    def _prepare_session(self):
        provisioned = load_json_as_dict(PROVISIOND_DIR, PROVISIOND_NAME)
        try:
            # 1. Create IAM Group
            for group in self.conf['group']:
                if arn := self._create_group(group['name'], group['policy']):
                    provisioned['iam_group'].update({group['name'] : arn})

            # 2. Create IAM User for teacher
            t = self.conf['teacher']
            for c in range(1, t['headcount']+1):
                if arn := self._create_iam_user(t['name_fmt'].format(c), t['pass'], t['group']):
                    provisioned['iam_user_teacher'].update({t['name_fmt'].format(c) : arn})

            # 3. Create IAM User for student
            s = self.conf['student']
            for c in range(1, s['headcount']+1):
                if arn := self._create_iam_user(s['name_fmt'].format(c), s['pass'], s['group']):
                    provisioned['iam_user_student'].update({s['name_fmt'].format(c) : arn})
        finally:
            save_dict_as_json('w', PROVISIOND_DIR, PROVISIOND_NAME, provisioned)

    def _clear_session(self):
        provisioned = load_json_as_dict(PROVISIOND_DIR, PROVISIOND_NAME)

        try:
            # 1. Destroy IAM User for student
            for name, arn in provisioned['iam_user_student'].items():
                if self._destroy_iam_user(name):
                    provisioned['iam_user_student'][name] = ''
            provisioned['iam_user_student'] = { name: arn for name, arn in provisioned['iam_user_student'].items() if arn != "" }

            # 2. Destroy IAM User for teacher
            for name, arn in provisioned['iam_user_teacher'].items():
                if self._destroy_iam_user(name):
                    provisioned['iam_user_teacher'][name] = ''
            provisioned['iam_user_teacher'] = { name: arn for name, arn in provisioned['iam_user_teacher'].items() if arn != "" }

            # 3. Destroy IAM Group
            for name, arn in provisioned['iam_group'].items():
                if self._destroy_iam_group(name):
                    provisioned['iam_group'][name] = ''
            provisioned['iam_group'] = { name:arn for name, arn in provisioned['iam_group'].items() if arn != "" }
        finally:
            save_dict_as_json('w', PROVISIOND_DIR, PROVISIOND_NAME, provisioned)

    def run(self):
        if not self._validate():
            LOGGER.error(f'Fail to get configuration file')
            return False

        self.cli = self.session.client('iam', config=self.cli_config)

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
    obj = IAMManager()
    obj.run()