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

        # For TLS SNI support
        'ndg-httpsclient>=0.4',
        'pyOpenSSL>=0.13',
        'pyasn1>=0.1.6',
    ],
)
