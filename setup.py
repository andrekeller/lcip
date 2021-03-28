#!/usr/bin/env python3

"""setup module for lcip"""

from setuptools import setup, find_packages

setup(
    name='lcip',
    version='1.0.0',
    description='LibVirt/cloud-init provisioner',
    long_description=(
        'Generate libvirt domain configuration and cloud-init seed iso '
        'for local provisioing of virtual machines using cloud images'
    ),
    author='André Keller',
    author_email='ak@0x2a.io',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Systems Administration',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    entry_points={
        'console_scripts': [
            'lcip = lcip.cli:provision'
        ]
    },
    install_requires=[
        'jinja2',
        'libvirt_python',
    ],
    packages=find_packages(),
    url='https://github.com/andrekeller/lcip',
)
