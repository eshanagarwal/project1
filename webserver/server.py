#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "ea2711"
DB_PASSWORD = "d73mng0a"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)



@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/')
def index():
  return redirect('/login')


@app.route('/home')
def home(uid):
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  print request.args

  query = '''
    SELECT 
      visitationlog.uid as uid, 
      visitationlog.rid as rid, 
      visitationlog.timestamp as timestamp, 
      studentuser.email as email, 
      restaurant.name as restaurant_name
    FROM visitationlog 
    INNER JOIN studentuser ON visitationlog.uid = studentuser.uid
    INNER JOIN restaurant ON visitationlog.rid = restaurant.rid
    WHERE studentuser.uid = '{}';
  '''.format(uid)
  
  cursor = g.conn.execute(query)

  data = []
  for result in cursor:
    data.append((result['uid'], result['rid'], result['timestamp'], result['email'], result['restaurant_name']))

  cursor.close()
  context = dict(data = data)


  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  return render_template("index.html", **context)


@app.route('/login')
def login():
    return render_template('login.html')

def login_validate(email, password):
  query = '''
    SELECT uid, password
    FROM studentuser
    WHERE email = '{}';
  '''.format(email)
  
  cursor = g.conn.execute(query)

  uid = -1
  for result in cursor:
    if result['password'] == password:
      uid = result['uid']

  cursor.close()

  return uid

@app.route('/login_submit', methods=['POST'])
def login_submit():

  uid = login_validate(request.form['email'], request.form['password'])

  if uid == -1:
    return render_template('login.html')

  return home(uid)

@app.route('/register_submit', methods=['POST'])
def register_submit():
  email = request.form['email_register']
  password = request.form['password_register']
  password_confirm = request.form['password_confirm']

  if password == password_confirm:
    query = '''
      INSERT INTO studentuser(email, password) VALUES (:email, :password);
    '''
    g.conn.execute(text(query), email = email, password = password);

  uid = login_validate(email, password)

  if uid == -1:
    return render_template('login.html')

  return home(uid)

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
