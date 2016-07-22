import flask

app = flask.Flask('mystery')

@app.route('/')
def index():
    return u'hello'
