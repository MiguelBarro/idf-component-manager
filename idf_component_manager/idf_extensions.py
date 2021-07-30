import sys

from idf_component_tools.errors import FatalError

from .core import ComponentManager

try:
    from typing import Any, Dict, List
except ImportError:
    pass

SERVICE_PROFILE = [
    {
        'names': ['--service-profile'],
        'help': 'Profile for component registry to use. By default profile named "default" will be used.',
        'envvar': 'IDF_COMPONENT_SERVICE_PROFILE',
    },
]  # type: List[Dict[str, Any]]

SERVICE_OPTIONS = SERVICE_PROFILE + [
    {
        'names': ['--name'],
        'help': 'Component name.',
        'required': True,
    },
    {
        'names': ['--namespace'],
        'help': 'Namespace for the component. Can be set in config file.',
        'envvar': 'IDF_COMPONENT_NAMESPACE',
    },
]  # type: List[Dict[str, Any]]

LOCAL_MANIFEST_OPTIONS = [
    {
        'names': ['--component'],
        'default': 'main',
        'show_default': True,
        'help': 'Name of the component in the project.',
    },
]


def action_extensions(base_actions, project_path):
    def callback(subcommand_name, ctx, args, **kwargs):
        try:
            manager = ComponentManager(args.project_dir)
            getattr(manager, str(subcommand_name).replace('-', '_'))(kwargs)
        except FatalError as e:
            print(e)
            sys.exit(e.exit_code)

    return {
        'actions': {
            'create-manifest': {
                'callback': callback,
                'help': 'Create manifest for specified component.',
                'options': LOCAL_MANIFEST_OPTIONS,
            },
            'add-dependency': {
                'callback': callback,
                'help': (
                    'Add dependency to the manifest file. '
                    'For now we only support adding dependencies from the component registry.'),
                'arguments': [
                    {
                        'names': ['dependency'],
                        'required': True,
                    },
                ],
                'options': LOCAL_MANIFEST_OPTIONS,
            },
            'create-remote-component': {
                'callback': callback,
                'help': 'Register a new component on the component registry.',
                'options': SERVICE_OPTIONS,
            },
            'upload-component': {
                'callback': callback,
                'help': 'Upload component to the component registry.',
                'options': SERVICE_OPTIONS + [
                    {
                        'names': ['--archive'],
                        'help': 'Path of the archive with a component to upload. '
                        'When not provided the component will be packed automatically.',
                    },
                    {
                        'names': ['--skip-pre-release'],
                        'help': 'Do not upload pre-release versions.',
                        'is_flag': True,
                        'default': False,
                    },
                    {
                        'names': ['--check-only'],
                        'help': 'Check if given component version is already uploaded and exit.',
                        'is_flag': True,
                        'default': False,
                    },
                ],
            },
            'delete-version': {
                'callback': callback,
                'help': 'Delete specified version of the component from the component registry.',
                'options': SERVICE_OPTIONS +
                [{
                    'names': ['--version'],
                    'help': 'Component version',
                    'required': True,
                }],
            },
            'upload-component-status': {
                'callback': callback,
                'help': 'Check the component uploading status by the job ID.',
                'options': SERVICE_PROFILE + [{
                    'names': ['--job'],
                    'help': 'Job ID',
                    'required': True,
                }],
            },
            'pack-component': {
                'callback': callback,
                'help': 'Create component archive and store it in the dist directory.',
                'options': SERVICE_OPTIONS,
            },
        },
    }
