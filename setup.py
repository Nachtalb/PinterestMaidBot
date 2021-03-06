#!/usr/bin/env python
from setuptools import setup, find_packages


setup(
    name='PinterestMaidBot',
    version='0.0.1dev',
    author='Nachtalb',
    author_email='na@nachtalb.io',
    license='GPL3',
    project_urls={
        'Bug Tracker': 'https://github.com/Nachtalb/PinterestMaidBot/issues',
        'Source Code': 'https://github.com/Nachtalb/PinterestMaidBot',
    },
    keywords='python telegram bot pinterest downloader',
    description='Download media from pinterest without any hassle',

    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['pinterestmaid'],
    include_package_data=True,
    zip_safe=False,

    install_requires=[
        'python-telegram-bot',
        'requests',
        'namedentities',
        'requests-html',
    ],

    classifiers=[
        'Operating System :: OS Independent',
        'Topic :: Communications :: Chat',
        'Topic :: Internet',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.9',
    ],
    entry_points={
        'console_scripts': [
            'bot = pinterestmaid.bot:main'
        ]
    }
)
