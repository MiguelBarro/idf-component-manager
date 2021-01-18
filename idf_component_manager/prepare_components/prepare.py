#!/usr/bin/env python
# coding=utf-8
#
# 'prepare.py' is a tool to be used by CMake build system to prepare components
# from package manager
#
#
# Copyright 2019 Espressif Systems (Shanghai) CO LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import sys

from idf_component_tools.errors import FatalError

from ..core import ComponentManager


def prepare_dep_dirs(args):
    ComponentManager(args.project_dir).prepare_dep_dirs(args.managed_components_list_file)


def inject_requirements(args):
    ComponentManager(args.project_dir).inject_requirements(args.component_requires_file)


def main():
    parser = argparse.ArgumentParser(
        description='Tool to be used by CMake build system to prepare components from package manager.')

    parser.add_argument('--project_dir', help='Project directory')

    subparsers = parser.add_subparsers(dest='step')
    subparsers.required = True

    prepare_step = subparsers.add_parser(
        'prepare_dependencies', help='Solve and download dependencies and provide directories to build system')
    prepare_step.set_defaults(func=prepare_dep_dirs)
    prepare_step.add_argument(
        '--managed_components_list_file', help='Path to file with list of managed component directories')

    inject_step_data = [
        {
            'name': 'inject_requirements',
        },
        {
            'name': 'inject_requrements',  # Workaroud for a typo in idf 4.1-4.2
            'extra_help': ' (alias)',
        }
    ]

    for step in inject_step_data:
        inject_step = subparsers.add_parser(
            step['name'], help='Inject requirements to CMake%s' % step.get('extra_help', ''))
        inject_step.set_defaults(func=inject_requirements)
        inject_step.add_argument('--build_properties_file', help='Path to temporary file with build properties')
        inject_step.add_argument('--component_properties_file', help='Path to temporary file with component properties')
        inject_step.add_argument('--component_requires_file', help='Path to temporary file with component requirements')
        inject_step.add_argument('--build_dir', help='Working directory for build process')
        inject_step.add_argument('--cmake_command', help='Path to CMake command')
        inject_step.add_argument('--idf_path', help='Path to IDF')

    args = parser.parse_args()

    try:
        args.func(args)
    except FatalError as e:
        print(e)
        sys.exit(2)