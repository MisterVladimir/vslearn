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
import setuptools
from typing import List

from vslearn import VERSION


def get_readme() -> str:
    readme_filename = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'README.md')
    with open(readme_filename, 'r') as f:
        return f.read()


def get_requirements() -> List[str]:
    with open('requirements.txt', 'r') as f:
        raw = f.read().replace(' ', '')
        return raw.split('\n')


if __name__ == '__main__':
    current_version = str(VERSION)
    url = r'https://github.com/MisterVladimir/vslearn'
    setuptools.setup(
        name='vslearn',
        packages=setuptools.find_packages(),
        version=current_version,
        ext_modules=[],
        python_requires='==3.6.*',
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
            'Programming Language :: Python :: 3.6'])
