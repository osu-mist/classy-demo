import os
import time

import flask
from flask import request

from . import api

TERM = '201603'
SUBJECT = 'CS'
SUBJECTNAME = 'Computer Science'

app = flask.Flask('mystery')
app.config.from_object('mystery.defaults')
if 'MYSTERY_CONFIG' in os.environ:
    app.config.from_envvar('MYSTERY_CONFIG')

@app.route('/')
def index():
    try:
        courses = get_all_courses(TERM, SUBJECT)
        error = None
    except api.APIError as e:
        error = e.message
        courses = []
    if 'all' not in request.args:
        courses = find_current_courses(courses, u'monday', u'1532')
    return flask.render_template('index.html',
        courses=courses,
        subject_name=SUBJECTNAME,
        error=error)

def get_all_courses(term, subject):
    # TODO: cache
    courses = []
    client = api.Client(app)

    page_number = 1
    while True:
        result = client.search(TERM, SUBJECT, page_size=100, page_number=page_number)
        if u'data' not in result or u'links' not in result:
            raise ValueError('invalid results returned from class search')
        courses.extend(result[u'data'])
        next = result[u'links'].get(u'next')
        if next is None:
            break
        page_number += 1

    return courses

def find_current_courses(courses, day, time):
    return [ course for course in courses if meets_at(course, day, time) ]

# day is monday, tuesday, wednesday, thursday, friday, saturday, or sunday.
# time is HHMM string
def meets_at(course, day, time):
    for meet in course.get(u'attributes', {}).get(u'meetingTimes', []):
        print meet
        if meet.get(day, False) and meet[u'startTime'] <= time <= meet[u'endTime']:
            return True
    return False
