# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import webbrowser

import click
import requests
from six.moves import input

from idf_component_manager.service_details import service_details
from idf_component_manager.utils import print_error, print_info
from idf_component_tools.api_client_errors import APIClientError
from idf_component_tools.config import ConfigManager
from idf_component_tools.errors import FatalError

from .constants import get_service_profile_option
from .utils import add_options


def init_registry():
    @click.group()
    def registry():
        """
        Group of commands to work with component registry
        """
        pass

    @registry.command()
    @add_options(get_service_profile_option())
    @click.option(
        '--no-browser',
        is_flag=True,
        default=False,
        help='Do not open browser and only print login URL to the terminal')
    @click.option(
        '--description',
        default='Token created through CLI login',
        help='Description for the token for future reference')
    def login(service_profile, no_browser, description):
        """
        Login to the component registry
        """

        # Load config to get
        config = ConfigManager().load()

        # Check if token is already in the profile
        profile = config.profiles.setdefault(service_profile, {})
        if 'api_token' in profile:
            raise FatalError(
                'You are already logged in with profile "{}", '
                'please either logout or use different profile'.format(service_profile))

        api_client, _ = service_details(service_profile=service_profile, token_required=False)

        auth_url = '{}/tokens/'.format(api_client.frontend_url)

        auth_params = {
            'scope': 'user write:components',
            'description': description,
        }
        auth_request = requests.Request('GET', auth_url, params=auth_params).prepare()

        if no_browser:
            print_info('Open this URL in your browser to login to the registry:\n\t{}'.format(auth_request.url))
        else:
            print_info('If browser did not open automatically please visit this URL:\n\t{}'.format(auth_request.url))
            webbrowser.open(auth_request.url, new=2, autoraise=True)

        # Wait for token
        print_info('Please create a token in the browser window and paste here')
        token_valid = False
        while not token_valid:
            token = input('Token:')

            try:
                api_client.auth_token = token
                api_client.token_information()
                token_valid = True
            except APIClientError as e:
                # Handle 401 and 403 explicitly
                print_error('Provided token does not seem to be working: {}\nPlease try again.'.format(e))
                continue

        # Save token to the profile
        profile['api_token'] = token
        ConfigManager().dump(config)

        print_info('Successfully logged in')

    @registry.command()
    @add_options(get_service_profile_option())
    def logout(service_profile):
        # Load config to get
        config = ConfigManager().load()

        # Check if token is already in the profile
        profile = config.profiles.setdefault(service_profile, {})
        if 'api_token' not in profile:
            raise FatalError('You are not logged in')

        del profile['api_token']
        ConfigManager().dump(config)

        print_info('Successfully logged out')

    return registry