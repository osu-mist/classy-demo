import os
ENDPOINT = "https://api.oregonstate.edu/v1"
if os.environ.get('CLASSY_ENDPOINT'):
    ENDPOINT = os.environ.get('CLASSY_ENDPOINT')
CLIENT_ID = os.environ.get('CLASSY_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('CLASSY_CLIENT_SECRET', '')
