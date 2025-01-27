# SPDX-FileCopyrightText: 2022-2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
"""Classes to work with Espressif Component Web Service"""
import os
import re
from collections import namedtuple
from functools import wraps
from io import open

from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
from schema import Schema
from tqdm import tqdm

from ..manifest import ComponentWithVersions
from .api_client_errors import APIClientError, NoRegistrySet
from .api_schemas import (
    API_INFORMATION_SCHEMA,
    API_TOKEN_SCHEMA,
    TASK_STATUS_SCHEMA,
    VERSION_UPLOAD_SCHEMA,
)
from .base_client import BaseClient, create_session
from .request_processor import base_request

# Import whole module to avoid circular dependencies

try:
    from typing import TYPE_CHECKING, Any, Callable

    if TYPE_CHECKING:
        from idf_component_tools.sources import BaseSource
except ImportError:
    pass

TaskStatus = namedtuple('TaskStatus', ['message', 'status', 'progress', 'warnings'])


def auth_required(f):  # type: (Callable) -> Callable
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        if not self.auth_token:
            raise APIClientError('API token is required')
        return f(self, *args, **kwargs)

    return wrapper


class APIClient(BaseClient):
    def __init__(self, base_url=None, auth_token=None):
        # type: (str | None, str | None) -> None
        super(APIClient, self).__init__()
        self.auth_token = auth_token
        self.base_url = base_url
        self._frontend_url = None

    def _request(cache=False):  # type: (BaseClient | bool) -> Callable
        def decorator(f):  # type: (Callable[..., Any]) -> Callable
            @wraps(f)  # type: ignore
            def wrapper(self, *args, **kwargs):
                url = self.base_url

                if url is None:
                    raise NoRegistrySet(
                        'The current operation requires access to the IDF component registry. '
                        'However, the registry URL is not set. You can set the '
                        'IDF_COMPONENT_REGISTRY_URL environment variable or "registry_url" field '
                        'for your current profile in "idf_component_manager.yml" file. '
                        'To use the default IDF component registry '
                        'unset IDF_COMPONENT_STORAGE_URL environment variable or remove '
                        '"storage_url" field from the "idf_component_manager.yml" file'
                    )

                session = create_session(cache=cache, token=self.auth_token)

                def request(
                    method,  # type: str
                    path,  # type: list[str]
                    data=None,  # type: dict | None
                    json=None,  # type: dict | None
                    headers=None,  # type: dict | None
                    schema=None,  # type: Schema | None
                ):
                    return base_request(
                        url,
                        session,
                        method,
                        path,
                        data=data,
                        json=json,
                        headers=headers,
                        schema=schema,
                    )

                return f(self, request=request, *args, **kwargs)

            return wrapper

        return decorator

    @property
    def frontend_url(self):
        if not self._frontend_url:
            self._frontend_url = re.sub(r'/api/?$', '', self.base_url)

        return self._frontend_url

    @_request(cache=True)
    def api_information(self, request):  # type: (Callable) -> dict
        return request('get', [], schema=API_INFORMATION_SCHEMA)

    @auth_required
    @_request(cache=False)
    def token_information(self, request):  # type: (Callable) -> dict
        return request('get', ['tokens', 'current'], schema=API_TOKEN_SCHEMA)

    def _upload_version_to_endpoint(self, request, file_path, endpoint):
        with open(file_path, 'rb') as file:
            filename = os.path.basename(file_path)

            encoder = MultipartEncoder({'file': (filename, file, 'application/octet-stream')})
            headers = {'Content-Type': encoder.content_type}

            progress_bar = tqdm(total=encoder.len, unit_scale=True, unit='B', disable=None)

            def callback(
                monitor, memo={'progress': 0}
            ):  # type: (MultipartEncoderMonitor, dict) -> None
                progress_bar.update(monitor.bytes_read - memo['progress'])
                memo['progress'] = monitor.bytes_read

            data = MultipartEncoderMonitor(encoder, callback)

            try:
                return request(
                    'post',
                    endpoint,
                    data=data,
                    headers=headers,
                    schema=VERSION_UPLOAD_SCHEMA,
                )['job_id']
            finally:
                progress_bar.close()

    @_request(cache=False)
    def versions(
        self, request, component_name, spec='*'
    ):  # type: (Callable, str, str) -> ComponentWithVersions
        """List of versions for given component with required spec"""
        return super(APIClient, self).versions(
            request=request, component_name=component_name, spec=spec
        )

    @auth_required
    @_request(cache=False)
    def upload_version(self, request, component_name, file_path):
        return self._upload_version_to_endpoint(
            request, file_path, ['components', component_name.lower(), 'versions']
        )

    @_request(cache=False)
    def validate_version(self, request, file_path):
        return self._upload_version_to_endpoint(request, file_path, ['components', 'validate'])

    @auth_required
    @_request(cache=False)
    def delete_version(
        self,
        request,  # type: Callable
        component_name,  # type: str
        component_version,  # type: str
    ):  # type: (...) -> None
        request('delete', ['components', component_name.lower(), component_version])

    @auth_required
    @_request(cache=False)
    def yank_version(
        self,
        request,  # type: Callable
        component_name,  # type: str
        component_version,  # type: str
        yank_message,  # type: str
    ):  # type: (...) -> None
        request(
            'post',
            ['components', component_name.lower(), component_version, 'yank'],
            json={'message': yank_message},
        )

    @_request(cache=False)
    def task_status(self, request, job_id):  # type: (Callable, str) -> TaskStatus
        body = request('get', ['tasks', job_id], schema=TASK_STATUS_SCHEMA)
        return TaskStatus(
            body['message'], body['status'], body['progress'], body.get('warnings', [])
        )
