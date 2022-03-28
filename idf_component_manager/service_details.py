''' Helper function to init API client'''
import os
from collections import namedtuple

from idf_component_tools.api_client import APIClient
from idf_component_tools.config import ConfigManager
from idf_component_tools.errors import FatalError
from idf_component_tools.sources.web_service import default_component_service_url

ServiceDetails = namedtuple('ServiceDetails', ['client', 'namespace'])


class NoSuchProfile(FatalError):
    pass


def service_details(
        namespace=None,  # type: str | None
        service_profile=None,  # type: str | None
        config_path=None  # type: str | None
):  # type: (...) -> ServiceDetails
    config = ConfigManager(path=config_path).load()
    profile_name = service_profile or 'default'
    profile = config.profiles.get(profile_name, {})

    if profile:
        print('Selected profile name from idf_component_manager.yml file: {}'.format(profile_name))
    elif profile_name != 'default' and not profile:
        raise NoSuchProfile('"{}" didn\'t find in idf_component_manager.yml file'.format(profile_name))

    # Priorities: DEFAULT_COMPONENT_SERVICE_URL env variable > profile value > built-in default
    service_url = default_component_service_url(service_profile=profile)

    # Priorities: idf.py option > IDF_COMPONENT_NAMESPACE env variable > profile value
    namespace = namespace or profile.get('default_namespace')
    if not namespace:
        raise FatalError('Namespace is required to upload component')

    # Priorities: IDF_COMPONENT_API_TOKEN env variable > profile value
    token = os.getenv('IDF_COMPONENT_API_TOKEN') or profile.get('api_token')
    if not token:
        raise FatalError('API token is required to upload component')

    client = APIClient(base_url=service_url, auth_token=token)

    return ServiceDetails(client, namespace)
