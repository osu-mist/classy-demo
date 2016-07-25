import os
import random
import re
from datetime import datetime

import flask
from flask import request

from . import api

TERM = '201603'
SUBJECT = 'CS'
CAMPUS = 'C' # Corvallis

SUBJECTS = {}
DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

time_re = re.compile(r'(?:[01][0-9]|2[0-3])(?:[0-5][0-9])')

app = flask.Flask('classy')
app.config.from_object('classy.defaults')
if 'CLASSY_CONFIG' in os.environ:
    app.config.from_envvar('CLASSY_CONFIG')

# TODO: use subjects API
def load_subjects():
    for line in app.open_resource('subjects'):
        line = line.strip()
        paren = line.rindex('(')
        name = line[:paren].strip()
        code = line[paren+1:-1].strip()
        SUBJECTS[code] = name

load_subjects()
assert SUBJECT in SUBJECTS

@app.route('/')
def index():
    subject = SUBJECT
    now = datetime.now()
    day = DAYS[now.weekday()]
    time = "{:02d}{:02d}".format(now.hour, now.minute)

    if 'subject' in request.args:
        if request.args['subject'] in SUBJECTS:
            subject = request.args['subject']
        elif request.args['subject'] == 'random':
            # TODO don't choose a subject with no classes
            subject = random.choice(SUBJECTS.keys())
            return flask.redirect(flask.url_for('index', subject=subject))

    subject_name = SUBJECTS[subject]

    if 'day' in request.args and request.args['day'] in DAYS:
        day = request.args['day']

    if 'time' in request.args and time_re.match(request.args['time']):
        time = request.args['time']


    try:
        courses = get_all_courses(TERM, subject)
        error = None
    except api.APIError as e:
        error = e.message
        courses = []

    courses = filter_courses(courses)
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

def get_all_courses(term, subject):
    # TODO: cache
    courses = []
    client = api.Client(app)

    page_number = 1
    while True:
        result = client.search(term, subject, page_size=100, page_number=page_number)
        if u'data' not in result or u'links' not in result:
            raise ValueError('invalid results returned from class search')
        courses.extend(result[u'data'])
        next = result[u'links'].get(u'next')
        if next is None:
            break
        page_number += 1

    return courses

def filter_courses(courses):
    """Filter out courses that aren't offered or have no meeting times"""
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
