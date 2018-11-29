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
import random
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

DATABASEURI = "postgresql://" + DB_USER + ":" + DB_PASSWORD + "@" + DB_SERVER + "/w4111"

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
        print
        "uh oh, problem connecting to database"
        import traceback;
        traceback.print_exc()
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
def home(uid=-1):
    """
    request is a special object that Flask provides to access web request information:
    request.method:   "GET" or "POST"
    request.form:     if the browser submitted a form, this contains the data in the form
    request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2
    See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
    """

    print (request.args)
    if int(uid) < 0:
      return index()

    feed_data = home_get_local_feed(uid)
    friend_data = home_get_friends_data(uid)
    sent_invites, received_invites = home_get_invites_data(uid)

    context = dict(
        uid=uid,
        feed_data=feed_data,
        friend_data=friend_data,
        sent_invites=sent_invites,
        received_invites=received_invites
    )

    return render_template("index.html", **context)


def home_get_local_feed(uid):
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
        WHERE studentuser.uid = :uid
        UNION ALL
        SELECT 
          visitationlog.uid as uid, 
          visitationlog.rid as rid, 
          visitationlog.timestamp as timestamp, 
          studentuser.email as email, 
          restaurant.name as restaurant_name
        FROM visitationlog
        INNER JOIN studentuser ON visitationlog.uid = studentuser.uid
        INNER JOIN restaurant ON visitationlog.rid = restaurant.rid
        WHERE studentuser.uid in (
          SELECT friendee
          FROM friends
          WHERE friender = :uid
        );
    '''

    cursor = g.conn.execute(text(query), uid=uid)

    feed_data = []
    for result in cursor:
        feed_data.append(
            (result['uid'], result['rid'], result['timestamp'], result['email'], result['restaurant_name']))

    cursor.close()
    return feed_data


def home_get_invites_data(uid):
    query = '''
    SELECT invitation.sendee as sendee, invitation.timestamp as timestamp, studentuser.email as email
    FROM invitation
    INNER JOIN studentuser ON invitation.sendee = studentuser.uid
    WHERE invitation.sender = :uid
  '''
    cursor = g.conn.execute(text(query), uid=uid);

    sent_invites = []
    for result in cursor:
        sent_invites.append((result["sendee"], result["email"], result["timestamp"]))

    query = '''
    SELECT invitation.sender as sender, invitation.timestamp as timestamp, studentuser.email as email
    FROM invitation
    INNER JOIN studentuser ON invitation.sender = studentuser.uid
    WHERE invitation.sendee = :uid
  '''
    cursor = g.conn.execute(text(query), uid=uid);

    received_invites = []
    for result in cursor:
        received_invites.append((result["sender"], result["email"], result["timestamp"],))

    return sent_invites, received_invites


def home_get_friends_data(uid):
    query = '''
    SELECT friends.friendee as friendee, studentuser.email as email
    FROM friends
    INNER JOIN studentuser ON friends.friendee = studentuser.uid
    WHERE friends.friender = :uid
  '''
    cursor = g.conn.execute(text(query), uid=uid);

    friend_data = []
    for result in cursor:
        friend_data.append((result["friendee"], result["email"]))

    return friend_data


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
    dorm_name = request.form['dorm_name']

    if password == password_confirm:
        query = '''
      INSERT INTO studentuser(email, password, dorm_name) VALUES (:email, :password, :dorm_name);
    '''
        g.conn.execute(text(query), email=email, password=password);

    uid = login_validate(email, password)

    if uid == -1:
        return render_template('login.html')

    return home(uid)


@app.route('/send_invite', methods=['POST'])
def send_invite():
    friend = request.form['invite']
    uid = request.form['uid']

    query = '''
    SELECT sender, sendee 
    FROM invitation
    WHERE sender = :uid
  '''
    cursor = g.conn.execute(text(query), uid=uid)

    invite_pair_present = False
    for result in cursor:
        if result['sendee'] == int(friend):
            invite_pair_present = True

    if invite_pair_present == True:
        query = '''
          UPDATE invitation
          SET timestamp = CURRENT_DATE
          WHERE sender = :uid AND sendee = :friend;
        '''
    else:
        query = '''
      INSERT INTO invitation(sender, sendee, timestamp) VALUES (:uid, :friend, CURRENT_DATE);
    '''

    g.conn.execute(text(query), uid=uid, friend=friend);

    return home(uid)


@app.route('/add_friend', methods=['POST'])
def add_friend():
    uid = request.form['uid']
    friend_email = request.form['friend_email']

    query = '''
    SELECT email, uid
    FROM studentuser
    WHERE email = :friend_email
  '''

    cursor = g.conn.execute(text(query), friend_email=friend_email)

    friend_uid = -1
    if cursor.rowcount == 0:
        # user does not exist
        return home(uid)
    else:
        for result in cursor:
            if result['email'] == friend_email:
                friend_uid = result['uid']

    if friend_uid == -1:
        return home(uid)
    if friend_uid == uid:
        return home(uid)

    query = '''
    SELECT friender, friendee, studentuser.email as email
    FROM friends
    INNER JOIN studentuser ON friends.friendee = studentuser.uid
    WHERE friends.friender = :uid
  '''
    cursor = g.conn.execute(text(query), uid=uid)

    for result in cursor:
        if result['email'] == friend_email:
            # friend pair already exists
            return home(uid)

    query = '''
    INSERT INTO friends(friender, friendee) VALUES 
      (:uid, :friend_uid),
      (:friend_uid, :uid)
  '''

    g.conn.execute(text(query), uid=uid, friend_uid=friend_uid);

    return home(uid)


@app.route('/recommendation', methods=['GET'])
def recommendation():
    if 'uid' in request.args:
      uid = request.args['uid']
    else:
      return index()

    context = dict(
      uid = uid
    )
    return render_template("recommendation.html", **context)


@app.route('/recommend', methods=['GET', 'POST'])
def recommend(rid = -1, name = ''):

    uid = request.form['uid']
    item_style = request.form['item_style']
    block_distance = request.form['block_distance']
    relative_cost = request.form['relative_cost']

    query = '''
    SELECT DISTINCT restaurant.name as name, restaurant.rid as rid
    FROM restaurant 
    INNER JOIN restaurantmenuitempair on restaurant.rid = restaurantmenuitempair.rid
    INNER JOIN  menuitem on restaurantmenuitempair.item_type = menuitem.item_type
    WHERE item_style = :item_style
    INTERSECT
    SELECT DISTINCT restaurant.name as name, restaurant.rid as rid
    FROM restaurant INNER JOIN restaurantdistance on restaurant.rid = restaurantdistance.rid
    INNER JOIN userlivesindorm on restaurantdistance.name = userlivesindorm.dorm_name
    WHERE uid = :uid AND block_distance <= :block_distance
    INTERSECT
    SELECT DISTINCT restaurant.name as name, restaurant.rid as rid
    FROM restaurant
    WHERE relative_cost <= :relative_cost
    LIMIT 1
    '''

    cursor = g.conn.execute(text(query), item_style=item_style, block_distance=block_distance,
                            relative_cost=relative_cost, uid=uid)
    recommendations = []
    for result in cursor:
        recommendations.append((result['rid'], result['name']))

    cursor.close()
    
    query = '''
      SELECT rid as rid
      FROM visitationlog
      WHERE uid = :uid
      LIMIT 2
    '''

    cursor = g.conn.execute(text(query), uid=uid)
    visits = []
    for result in cursor:
        visits.append(result['rid'])

    cursor.close()

    rec = -1
    for i in visits:
        for j in recommendations:
            if i == j & (len(recommendations) > 1):
                recommendations.remove(j)


    if len(recommendations) > 0:
      rid = recommendations[0][0]
      query = '''
        INSERT INTO visitationlog(uid, rid, timestamp) VALUES 
          (:uid, :rid, CURRENT_DATE)
      '''
      cursor = g.conn.execute(text(query), uid=uid, rid=rid)
      cursor.close()

    context = dict(
        uid=uid,
        recommendations=recommendations
    )
    return render_template("recommendation.html", **context)

@app.route('/restaurants', methods=['GET'])
def restaurants(rid = -1, location='', menu_details=[], ratings=[], comments = {}):
  if 'uid' in request.args:
    uid = request.args['uid']
  else:
    return index()

  query = '''
    SELECT DISTINCT restaurant.name as name
    FROM restaurant 
  '''

  cursor = g.conn.execute(text(query))
  restaurants = []
  for result in cursor:
      restaurants.append(result['name'])

  cursor.close()

  context = dict(
    uid = uid,
    rid = rid,
    restaurants = restaurants,
    location = location,
    menu_details = menu_details,
    ratings = ratings,
    comments = comments
  )
  return render_template("restaurants.html", **context)

@app.route('/view_restaurant_details', methods=['GET', 'POST'])
def view_restaurant_details():
  chosen_rest = request.form['chosen_restaurant']
  query = '''
    SELECT rid, location 
    FROM restaurant 
    WHERE name = :chosen_rest
  '''

  cursor = g.conn.execute(text(query), chosen_rest = chosen_rest)
  location = ''
  rid = -1
  for result in cursor:
      location = result['location']
      rid = result['rid']
  cursor.close()

  if rid < 0:
    return restaurants()

  query_menu = '''
    SELECT item_type, price
    FROM RestaurantMenuItemPair
    WHERE rid = :rid
  '''
  cursor = g.conn.execute(text(query_menu), rid = rid)
  menu_details = []
  for result in cursor:
    menu_details.append((result["item_type"], result["price"]))

  cursor.close()

  query_reviews = '''
    SELECT *
    FROM rating
    WHERE rid = :rid
  '''
  cursor = g.conn.execute(text(query_reviews), rid = rid)
  ratings = []
  for result in cursor:
    ratings.append((result["rating_id"], result["stars"], result["review"]))
  cursor.close()

  query_comments = '''
    SELECT *
    FROM ratingcomment
    WHERE rating_id IN (
      SELECT rating_id
      FROM rating
      WHERE rid = :rid
    )
  '''
  cursor = g.conn.execute(text(query_comments), rid = rid)
  comments = {}
  for result in cursor:
    if result['rating_id'] in comments:
      comments[result['rating_id']].append(result['comment_body'])
    else:
      comments[result['rating_id']] = [result['comment_body']]

  cursor.close()

  return restaurants(rid = rid, location=location, menu_details = menu_details, ratings=ratings, comments = comments)

@app.route('/add_rating')
def add_rating():
  review_text = request.form["new_review"]
  stars = request.form["stars"]

  query = '''
    INSERT INTO rating(uid, rid, stars, review) VALUES 
      (:uid, :rid, :stars, :review_text)
  '''

  return

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
        print
        "running on %s:%d" % (HOST, PORT)
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


    run()
