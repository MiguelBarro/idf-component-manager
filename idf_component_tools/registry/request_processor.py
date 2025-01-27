# SPDX-FileCopyrightText: 2023 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
import os

import requests
from requests import Response
from schema import Schema, SchemaError

from idf_component_tools.registry.api_schemas import ERROR_SCHEMA

from .api_client_errors import (
    KNOWN_API_ERRORS,
    APIClientError,
    NetworkConnectionError,
    StorageFileNotFound,
)

DEFAULT_TIMEOUT = (6.05, 30.1)  # Connect timeout  # Read timeout


def join_url(*args):  # type: (*str) -> str
    """
    Joins given arguments into an url and add trailing slash
    """
    parts = [part[:-1] if part and part[-1] == '/' else part for part in args]
    return '/'.join(parts)


def get_timeout():  # type: () -> float | tuple[float, float]
    try:
        return float(os.environ['IDF_COMPONENT_SERVICE_TIMEOUT'])
    except ValueError:
        raise APIClientError(
            'Cannot parse IDF_COMPONENT_SERVICE_TIMEOUT. It should be a number in seconds.'
        )
    except KeyError:
        return DEFAULT_TIMEOUT


def make_request(
    method,  # type: str
    session,  # type: requests.Session
    endpoint,  # type: str
    data,  # type: dict | None
    json,  # type: dict | None
    headers,  # type: dict | None
    timeout,  # type: float | tuple[float, float]
):  # type: (...) -> Response
    try:
        response = session.request(
            method,
            endpoint,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )
    except requests.exceptions.ConnectionError as e:
        raise NetworkConnectionError(str(e))
    except requests.exceptions.RequestException:
        raise APIClientError('HTTP request error')

    return response


def handle_response_errors(
    response,  # type:  requests.Response
    endpoint,  # type:  str
    use_storage,  # type:  bool
):  # type: (...) -> dict
    if response.status_code == 204:  # NO CONTENT
        return {}
    elif 400 <= response.status_code < 500:
        if use_storage:
            if response.status_code == 404:
                raise StorageFileNotFound()
            raise APIClientError(
                'Error during request.\nStatus code: {}'.format(response.status_code)
            )
        handle_4xx_error(response)
    elif 500 <= response.status_code < 600:
        raise APIClientError(
            'Internal server error happened while processing request to: {}\nStatus code: {}'.format(
                endpoint, response.status_code
            )
        )

    return response.json()


def handle_4xx_error(error):  # type: (requests.Response) -> None
    try:
        json = ERROR_SCHEMA.validate(error.json())
        name = json['error']
        messages = json['messages']
    except SchemaError as e:
        raise APIClientError(
            'API Endpoint "{}: returned unexpected error description:\n{}'.format(error.url, str(e))
        )
    except ValueError:
        raise APIClientError('Server returned an error in unexpected format')

    exception = KNOWN_API_ERRORS.get(name, APIClientError)
    if isinstance(messages, list):
        raise exception('\n'.join(messages))
    else:
        raise exception(
            'Error during request:\n{}\nStatus code: {} Error code: {}'.format(
                str(messages), error.status_code, name
            )
        )


def validate_response(
    response_json,  # type: dict
    schema,  # type:  Schema | None
    endpoint,  # type: str
):  # type: (...) -> dict
    try:
        if schema is not None:
            schema.validate(response_json)
    except SchemaError as e:
        raise APIClientError(
            'API Endpoint "{}: returned unexpected JSON:\n{}'.format(endpoint, str(e))
        )
    except (ValueError, KeyError, IndexError):
        raise APIClientError('Unexpected component server response')

    return response_json


def base_request(
    url,  # type: str
    session,  # type: requests.Session
    method,  # type: str
    path,  # type: list[str]
    data=None,  # type: dict | None
    json=None,  # type: dict | None
    headers=None,  # type: dict | None
    schema=None,  # type: Schema
    use_storage=False,  # type: bool
):  # type: (...) -> dict
    endpoint = join_url(url, *path)
    timeout = get_timeout()
    response = make_request(method, session, endpoint, data, json, headers, timeout)
    response_json = handle_response_errors(response, endpoint, use_storage)
    return validate_response(response_json, schema, endpoint)
