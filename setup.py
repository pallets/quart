import os
import sys

from setuptools import setup, find_packages

if sys.version_info < (3,7,0):
    sys.exit('Python 3.7.0 is the minimum required version')

PROJECT_ROOT = os.path.dirname(__file__)

about = {}
with open(os.path.join(PROJECT_ROOT, 'quart', '__about__.py')) as file_:
    exec(file_.read(), about)

with open(os.path.join(PROJECT_ROOT, 'README.rst')) as file_:
    long_description = file_.read()

INSTALL_REQUIRES = [
    'aiofiles',
    'blinker',
    'click',
    'hypercorn >= 0.6.0',
    'itsdangerous',
    'jinja2',
    'multidict',
    'sortedcontainers',
]

setup(
    name='Quart',
    version=about['__version__'],
    python_requires='>=3.7.0',
    description="A Python ASGI web microframework with the same API as Flask",
    long_description=long_description,
    url='https://gitlab.com/pgjones/quart/',
    author='P G Jones',
    author_email='philip.graham.jones@googlemail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=find_packages(exclude=["tests", "tests.*"]),
    py_modules=['quart'],
    install_requires=INSTALL_REQUIRES,
    tests_require=INSTALL_REQUIRES + [
        'asynctest',
        'hypothesis',
        'pytest',
        'pytest-asyncio',
    ],
    extras_require={
        'dotenv': ['python-dotenv'],
    },
    entry_points={
        'console_scripts': ['quart=quart.cli:main'],
    },
    include_package_data=True,
)
