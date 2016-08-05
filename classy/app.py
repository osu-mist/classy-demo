import os
import random
import re
from datetime import datetime

import lru

import flask
from flask import request

from . import api

SUBJECTS = {}
DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
_current_term = None
_course_cache = lru.LRU(100)

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

def get_current_term(client, _now=datetime.now):
    """Fetch the term object for the term which is currently in session.
       Returns None if no term is in session"""

    global _current_term

    # do we already know the current term?
    today = _now().strftime("%Y-%m-%d")
    if _current_term:
        if today < _current_term[u'attributes'][u'startDate']:
            # the current term hasn't started yet
            return None
        elif today <= _current_term[u'attributes'][u'endDate']:
            # this is the current term
            return _current_term
        else:
            # the current term is over
            _current_term = None

    # we don't know what the current term is

    # fetch the list of open terms
    terms = client.open_terms()
    terms = terms.get(u'data', [])

    # fetch the actual term data
    # XXX
    for i, term in enumerate(terms):
        terms[i] = client.term(term[u'id']).get(u'data', {})

    # try to find the term that's happening right now
    for term in terms:
        start_date = term[u'attributes'].get(u'startDate', u'xxx')
        end_date = term[u'attributes'].get(u'endDate', u'xxx')
        if start_date <= today <= end_date:
            _current_term = term
            return _current_term

    # if there are no terms open right now,
    # set the current term to the next closest term
    # and return None
    terms.sort(key=lambda x: x[u'attributes'][u'startDate'])
    for term in terms:
        if today < term[u'attributes'].get(u'startDate'):
            _current_term = term
            return None

    # struck out
    _current_term = None
    return None

@app.route('/')
def index():
    term_code = None
    subject = 'random'
    now = datetime.now()
    day = DAYS[now.weekday()]
    time = "{:02d}{:02d}".format(now.hour, now.minute)

    # Parse query args
    # With the exception of subject,
    # these are mostly for testing
    if 'term' in request.args:
        term_code = request.args['term']

    if 'subject' in request.args:
        if request.args['subject'] in SUBJECTS or request.args['subject'] == 'random':
            subject = request.args['subject']

    if 'day' in request.args and request.args['day'] in DAYS:
        day = request.args['day']

    if 'time' in request.args and time_re.match(request.args['time']):
        time = request.args['time']


    # Fetch the current term,
    client = api.Client(app)

    if term_code is not None:
        term = client.term(term_code)[u'data']
        if term[u'id'] is None:
            # XXX not the right error message,
            # but term= is just a debugging param anyway
            return flask.render_template('noterms.html')
    else:
        term = get_current_term(client)
        if term is None:
            return flask.render_template('noterms.html')

    # Choose a random subject, if necessary
    if subject == 'random':
        # TODO don't choose a subject with no classes
        subject = random.choice(SUBJECTS.keys())
        return flask.redirect(flask.url_for('index', subject=subject))

    subject_name = SUBJECTS[subject]

    # Fetch the course list
    # or retrieve from cache
    error = None
    cache_key = term[u'id'], subject
    if cache_key in _course_cache:
        courses = _course_cache[cache_key]
    else:
        try:
            courses = get_all_courses(client, term[u'id'], subject)
        except api.APIError as e:
            error = e.message
            courses = []
        else:
            courses = filter_courses(courses)
            _course_cache[cache_key] = courses

    # Select just the courses happening now
    courses = find_current_courses(courses, day, time)

    # Choose a random course
    if courses:
        # choose a random course
        # TODO prefer large courses
        # TODO prefer courses that are not full
        random_course = random.choice(courses)
        meeting_time = get_meeting_time(random_course, day, time)
    else:
        random_course = None
        meeting_time = None

    # Render the page
    return flask.render_template('index.html',
        random_course=random_course,
        meeting_time=meeting_time,
        subject_name=subject_name,
        number_of_courses=len(courses),
        current_term=term,
        error=error)

@app.route('/subjects')
def list_subjects():
    return flask.render_template('subjects.html',
        subjects=SUBJECTS)

def get_all_courses(client, term, subject):
    # TODO: cache
    courses = []

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
