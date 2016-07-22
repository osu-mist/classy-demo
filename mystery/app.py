import os

import flask
from flask import request

from . import api

TERM = '201701'
SUBJECT = 'CS'

app = flask.Flask('mystery')
app.config.from_object('mystery.defaults')
if 'MYSTERY_CONFIG' in os.environ:
    app.config.from_envvar('MYSTERY_CONFIG')

@app.route('/')
def index():
    client = api.Client(app)
    try:
        result = client.search(TERM, SUBJECT)
    except api.APIError as e:
        result = e.message
    return flask.render_template('index.html', result=result)
