# -*- coding: utf-8 -*-
"""
@author: Vladimir Shteyn
@email: vladimir@shteyn.net

Copyright Vladimir Shteyn, 2019

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import os
import pkg_resources
import setuptools
import sys
from typing import List, Optional, TypeVar, Union

from vslearn import VERSION


CURDIR = os.path.dirname(os.path.abspath(__file__))


def get_readme() -> str:
    readme_filename = os.path.join(CURDIR, 'README.md')
    with open(readme_filename, 'r') as f:
        return f.read()


def convert_tensorflow_version(requirement: str) -> str:
    """
    Only upgrade tensorflow GPU if GPU version already installed. Otherwise
    default to installing CPU with correct version.
    # XXX what happens to tensorflow-gpu built from source?
    """
    if 'tensorflow' in requirement:
        try:
            import tensorflow as tf
        except ImportError:
            pass
        else:
            if tf.test.is_gpu_available():
                requirement = requirement.replace(
                    'tensorflow', 'tensorflow-gpu')

    return requirement


def get_requirements() -> List[str]:
    def read_requirments_file(filename: str) -> List[str]:
        with open(filename, 'r') as f:
            raw: str = f.read().replace(' ', '')
        return raw.split('\n')

    version_error_message: str = \
        'Python version is {}.'.format(sys.version) + \
        'vslearn is only compatible with Python 3.6 and 3.7'

    base_requirements_filename: str = os.path.join(
        CURDIR, 'common_requirements.txt')
    assert sys.version_info[0] == 3, version_error_message
    python_minor_version: int = sys.version_info[1]
    requirements: List[str] = read_requirments_file(base_requirements_filename)
    extra_requirements: List[str] = []

    if python_minor_version == 6:
        py36_requirements_filename: str = os.path.join(
            CURDIR, 'py36_requirements.txt')
        extra_requirements += read_requirments_file(
            py36_requirements_filename)
    elif python_minor_version == 7:
        py37_requirements_filename: str = os.path.join(
            CURDIR, 'py37_requirements.txt')
        extra_requirements += read_requirments_file(
            py37_requirements_filename)
    else:
        raise ValueError(version_error_message)

    converted_requirements: List[str] = [
        convert_tensorflow_version(r) for r in extra_requirements]
    requirements += converted_requirements
    return requirements


if __name__ == '__main__':
    current_version = str(VERSION)
    url = r'https://github.com/MisterVladimir/vslearn'
    setuptools.setup(
        name='vslearn',
        packages=setuptools.find_packages(),
        version=current_version,
        ext_modules=[],
        python_requires='>=3.6.*',
        install_requires=get_requirements(),
        setup_requires=["pytest-runner"],
        tests_require=["pytest", "pytest-qt", "pytest-cov"],
        include_package_data=True,
        author='Vladimir Shteyn',
        author_email='vladimir@shteyn.net',
        url=url,
        download_url='{}/archive/{}.tar.gz'.format(url, current_version),
        long_description=get_readme(),
        long_description_content_type='text/markdown',
        license="GNUv3",
        classifiers=[
            'Intended Audience :: Science/Research',
            'Development Status :: 3 - Alpha',
            'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
            'Topic :: Scientific/Engineering :: Medical Science Apps.',
            'Topic :: Scientific/Engineering :: Visualization',
            'Topic :: Scientific/Engineering :: Image Recognition',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7'])
