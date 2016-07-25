# classy.api - communicates with the class-search api

import requests
from werkzeug.utils import cached_property

class Error(Exception):
    """API error base class"""

class AuthError(Error):
    """Not authorized"""

class NotFoundError(Error):
    """Not found"""

class APIError(Error):
    """developer error"""

class Client(object):
    def __init__(self, app):
        self.client_id = app.config['CLIENT_ID']
        self.client_secret = app.config['CLIENT_SECRET']
        self.endpoint = app.config['ENDPOINT']
        self.token_endpoint = self.endpoint + '/token'

    def get_url(self, url, params=None):
        access_token = self.access_token
        headers = {'Authorization': "Bearer "+access_token}
        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 401:
            raise AuthError('not authorized')
        elif response.status_code == 404:
            raise NotFoundError('key not found')
        elif response.status_code == 400:
            raise APIError(response.json())
        elif response.status_code != 200:
            raise Error('HTTP error')

        return response.json()

    def search(self,
            term,
            subject,
            course_number=None,
            q=None,
            page_size=None,
            page_number=None):

        params = {
            'term': term,
            'subject': subject,
        }
        if course_number is not None:
            params['courseNumber'] = course_number
        if q is not None:
            params['q'] = q
        if page_size is not None:
            params['page[size]'] = page_size
        if page_number is not None:
            params['page[number]'] = page_number

        return self.get_url(self.endpoint, params=params)

    @cached_property
    def access_token(self):
        return self._get_access_token()

    def _get_access_token(self):
        if self.token_endpoint is None:
            return ''
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials',
        }
        response = requests.post(self.token_endpoint, data=payload)
        if response.status_code == 401:
            raise AuthError("couldn't get access token")
        elif response.status_code != 200:
            raise Error('HTTP error')

        try:
            obj = response.json()
            obj['token_type']
            obj['access_token']
        except (ValueError, KeyError):
            raise Error("couldn't decode json")

        # FIXME: Remove BearerToken when apigee correctly returns Bearer
        if obj['token_type'] not in ('Bearer', 'BearerToken'):
            raise AuthError('invalid token type')

        return obj['access_token']
