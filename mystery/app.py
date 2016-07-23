import os
import random
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

    courses = filter_courses(courses)

    day = u'monday'
    hour = u'1532'
    all = ('all' in request.args)

    if 'all' not in request.args:
        courses = find_current_courses(courses, day, hour)

    if courses:
        # choose a random course
        # TODO prefer courses that are not full
        random_course = random.choice(courses)
        meeting_time = get_meeting_time(random_course, day, hour)
        if all:
            meeting_time = random.choice(random_course[u'attributes'][u'meetingTimes'])
    else:
        random_course = None
        meeting_time = None

    return flask.render_template('index.html',
        random_course=random_course,
        meeting_time=meeting_time,
        courses=courses,
        subject_name=SUBJECTNAME,
        number_of_courses=len(courses),
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

def filter_courses(courses):
    return [ course for course in courses if common_sense(course) ]

def common_sense(course):
    # Filter out courses that aren't even being offered
    # or are somebody's thesis or something
    if course[u'attributes'].get(u'maximumEnrollment') < 10:
        return False

    # Filter out courses with no meeting times
    times = course[u'attributes'].get(u'meetingTimes', [])
    if not any(meet.get('startTime') is not None for meet in times):
        return False

    return True

def find_current_courses(courses, day, time):
    return [ course for course in courses if meets_at(course, day, time) ]

# day is monday, tuesday, wednesday, thursday, friday, saturday, or sunday.
# time is HHMM string
def meets_at(course, day, time):
    for meet in course[u'attributes'].get(u'meetingTimes', []):
        if meet.get(day, False) and meet[u'startTime'] <= time <= meet[u'endTime']:
            return True
    return False

def get_meeting_time(course, day, time):
    for meet in course[u'attributes'].get(u'meetingTimes', []):
        if meet.get(day, False) and meet[u'startTime'] <= time <= meet[u'endTime']:
            return meet
    return None
