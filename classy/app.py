import os
import random
import re
from datetime import datetime

import flask
from flask import request

from . import api

TERM = '201603'

SUBJECTS = {}
DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

time_re = re.compile(r'(?:[01][0-9]|2[0-3])(?:[0-5][0-9])')

app = flask.Flask('classy')
app.config.from_object('classy.defaults')
if 'CLASSY_CONFIG' in os.environ:
    app.config.from_envvar('CLASSY_CONFIG')

@app.before_first_request
def load_subjects():
    SUBJECTS.clear()
    client = api.Client(app)
    # TODO error handling
    response = client.subjects()
    for subject in response['data']:
        abbr = subject[u'attributes'][u'abbreviation']
        title = subject[u'attributes'][u'title']
        if abbr == '0000':
            # Subject Unknown
            continue
        if title.startswith(u'OS/'):
            # overseas studies
            continue
        SUBJECTS[abbr] = title

_course_cache = {}

@app.route('/')
def index():
    subject = 'random'
    now = datetime.now()
    day = DAYS[now.weekday()]
    time = "{:02d}{:02d}".format(now.hour, now.minute)

    if 'subject' in request.args:
        if request.args['subject'] in SUBJECTS or request.args['subject'] == 'random':
            subject = request.args['subject']

    if 'day' in request.args and request.args['day'] in DAYS:
        day = request.args['day']

    if 'time' in request.args and time_re.match(request.args['time']):
        time = request.args['time']


    if subject == 'random':
        # TODO don't choose a subject with no classes
        subject = random.choice(SUBJECTS.keys())
        return flask.redirect(flask.url_for('index', subject=subject))

    subject_name = SUBJECTS[subject]


    error = None
    if subject not in _course_cache:
        try:
            courses = get_all_courses(TERM, subject)
        except api.APIError as e:
            error = e.message
            courses = []
        else:
            courses = filter_courses(courses)
            _course_cache[subject] = courses

    courses = _course_cache[subject]
    courses = find_current_courses(courses, day, time)

    if courses:
        # choose a random course
        # TODO prefer large courses
        # TODO prefer courses that are not full
        random_course = random.choice(courses)
        meeting_time = get_meeting_time(random_course, day, time)
    else:
        random_course = None
        meeting_time = None

    return flask.render_template('index.html',
        random_course=random_course,
        meeting_time=meeting_time,
        subject_name=subject_name,
        number_of_courses=len(courses),
        error=error)

@app.route('/subjects')
def list_subjects():
    return flask.render_template('subjects.html',
        subjects=SUBJECTS)

def get_all_courses(term, subject):
    # TODO: cache
    courses = []
    client = api.Client(app)

    page_number = 1
    while True:
        result = client.courses(term, subject, page_size=100, page_number=page_number)
        if u'data' not in result or u'links' not in result:
            raise ValueError('invalid results returned from class search')
        courses.extend(result[u'data'])
        if not result[u'links'] or not result[u'links'][u'next']:
            break
        page_number += 1

    return courses

def filter_courses(courses):
    """Filter out courses that aren't offered or have no meeting times"""
    return [ course for course in courses if common_sense(course) ]

def common_sense(course):
    if not isinstance(course.get(u'attributes'), dict):
        return False

    # Filter out non-lecture classes
    if course[u'attributes'].get(u'scheduleTypeDescription', u'') != u'Lecture':
        return False

    # Filter out courses that aren't even being offered
    # or are super small
    if course[u'attributes'].get(u'maximumEnrollment') < 10:
        return False

    # Filter out courses with no meeting times
    # (such as ecampus classes)
    times = course[u'attributes'].get(u'meetingTimes', [])
    if not any(meet.get('startTime') is not None for meet in times):
        return False

    return True

def find_current_courses(courses, day, time):
    """Filter courses which meet on the given day and time

    day is monday, tuesday, wednesday, thursday, friday, saturday, or sunday.
    time is HHMM string
    """
    return [ course for course in courses if meets_at(course, day, time) ]

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
