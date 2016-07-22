from setuptools import setup

setup(
    name='mystery-app',
    version='0.1',
    author='Andrew Ekstedt',
    author_email='ekstedta@oregonstate.edu',
    packages = [
        'mystery',
    ],
    install_requires = [
        'Flask>=0.10',
        'requests>=2.9',
    ],
)
