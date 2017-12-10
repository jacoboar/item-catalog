import random
import string
import httplib2
import json
import requests
from flask import Flask, render_template, request, redirect, url_for
from flask import jsonify, flash, Response, make_response
from flask import session as login_session
from sqlalchemy import desc
from database_setup import Country, Team, User, DBSession
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from functools import wraps


CLIENT_ID = json.loads(open('client_secret.json', 'r').read())[
    'web']['client_id']
APPLICATION_NAME = "Item Catalog App"
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
session = DBSession()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            flash("You need to be logged in to add a new team.")
            return redirect(url_for('getIndex'))
    return decorated_function


def nameExists(name):
    results = session.query(Team).filter_by(name=name).all()
    return len(results) > 0


def get_user(name):
    try:
        user = session.query(User).filter_by(name=name).one()
        return user.id
    except:
        return None


def create_user(login_session):
    username = login_session['username']
    new_user = User(name=username)
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(name=username).one()
    return user.id


@app.route('/')
def index():
    return redirect(url_for('getIndex'))


@app.route('/catalog/JSON')
def getCatalog():
    # Returns JSON version of the catalog
    output_json = []
    countries = session.query(Country).all()
    for country in countries:
        teams = session.query(Team).filter_by(country_id=country.id)
        country_output = {}
        country_output["id"] = country.id
        country_output["name"] = country.name
        country_output["teams"] = [t.serialize for t in teams]
        output_json.append(country_output)
    return jsonify(Countries=output_json)


@app.route('/catalog/teams/<team_id>/JSON')
def getTeam(team_id):
    # Returns JSON data of an arbitrary team
    output_json = []
    team = session.query(Team).filter_by(name=team_id).one()
    team_output = {}
    team_output["id"] = team.id
    team_output["name"] = team.name
    team_output["description"] = team.description
    team_output["country_id"] = team.country_id
    output_json.append(team_output)
    return jsonify(Team=output_json)


@app.route('/catalog', methods=['GET', 'POST'])
def getIndex():
    try:
        user = login_session['username']
    except KeyError:
        user = None
    if request.method == 'GET':
        STATE = ''.join(random.choice(string.ascii_uppercase +
                                      string.digits) for x in xrange(32))
        login_session['state'] = STATE
        countries = session.query(Country).all()
        latest_teams = session.query(Team).order_by(
            desc(Team.date)).all()
        country_names = {}
        for country in countries:
            country_names[country.id] = country.name
        if len(latest_teams) == 0:
            flash("No teams found")
        return render_template(
            'country.html', countries=countries, teams=latest_teams,
            country_names=country_names, user=user, STATE=STATE
        )
    else:
        print ("Starting authentication")
        if request.args.get('state') != login_session['state']:
            response = make_response(json.dumps(
                'Invalid state parameter.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response
        # Get authorization code
        code = request.data

        try:
            oauth_flow = flow_from_clientsecrets(
                'client_secret.json', scope='')
            oauth_flow.redirect_uri = 'postmessage'
            credentials = oauth_flow.step2_exchange(code)
        except FlowExchangeError:
            response = make_response(
                json.dumps('Failed to upgrade the authorization code.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response

        access_token = credentials.access_token
        url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
               % access_token)
        h = httplib2.Http()
        result = json.loads(h.request(url, 'GET')[1])
        if result.get('error') is not None:
            response = make_response(
                       json.dumps(result.get('error')), 500)
            response.headers['Content-Type'] = 'application/json'

        gplus_id = credentials.id_token['sub']
        if result['user_id'] != gplus_id:
            response = make_response(json.dumps(
                "Token's user ID doesn't match given user ID."), 401)
            response.headers['Content-Type'] = 'application/json'
            return response

        if result['issued_to'] != CLIENT_ID:
            response = make_response(
                json.dumps("Token's client ID does not match app's."), 401)
            print "Token's client ID does not match app's."
            response.headers['Content-Type'] = 'application/json'
            return response

        stored_credentials = login_session.get('credentials')
        stored_gplus_id = login_session.get('gplus_id')
        if stored_credentials is not None and gplus_id == stored_gplus_id:
            response = make_response(json.dumps(
                'Current user is already connected.'), 200)
            response.headers['Content-Type'] = 'application/json'
            return response

        # Store the access token in the session
        login_session['access_token'] = credentials.access_token
        login_session['gplus_id'] = gplus_id

        # Get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        params = {'access_token': credentials.access_token, 'alt': 'json'}
        answer = requests.get(userinfo_url, params=params)
        data = answer.json()
        login_session['username'] = data['name']

        user_id = get_user(data['name'])
        if not user_id:
            user_id = create_user(login_session)
        login_session['user_id'] = user_id

        flash("you are now logged in as %s" % login_session['username'])
        return redirect(url_for('getIndex'))


@app.route('/logout')
def logout():
    access_token = login_session['access_token']
    print 'In logout access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http(disable_ssl_certificate_validation=True)
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return redirect(url_for('getIndex'))
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/catalog/countries/<country_name>/')
def getTeams(country_name):
    countries = session.query(Country).all()
    selected_country = session.query(
        Country).filter_by(name=country_name).one()
    teams = session.query(Team).filter_by(
        country_id=selected_country.id).all()
    country_names = {}
    for country in countries:
        country_names[country.id] = country.name
    if len(teams) == 0:
        flash("No teams found in this country")
    try:
        user = login_session['username']
    except KeyError:
        user = None
    return render_template(
        'teams.html', selected_country=selected_country,  user=user,
        teams=teams, countries=countries, country_names=country_names
    )


@app.route('/catalog/teams/<team_name>/')
def getTeamDetails(team_name):
    team = session.query(Team).filter_by(name=team_name).one()
    country = session.query(Country).filter_by(id=team.country_id).one()
    return render_template(
        'team.html', team=team, country=country
    )


@app.route('/catalog/teams/new', methods=['GET', 'POST'])
@login_required
def newTeam():
    countries = session.query(Country).all()
    try:
        user = login_session['username']
    except KeyError:
        user = None
    if request.method == 'POST':
        name = request.form['name']
        if nameExists(name):
            flash("Please enter a different team. Team " +
                  name + " already exists.")
            return redirect(url_for('newItem'))
        user_id = get_user(login_session['username'])
        newTeam = Team(name,
                       request.form['description'],
                       request.form['country_id'],
                       user_id)
        session.add(newTeam)
        session.commit()
        return redirect(url_for('getIndex'))
    else:
        return render_template(
            'create.html',  countries=countries, user=user
        )


@app.route('/catalog/teams/<team_name>/delete', methods=['GET', 'POST'])
@login_required
def deleteTeam(team_name):
    team = session.query(Team).filter_by(name=team_name).one()
    if team.user_id != login_session['user_id']:
        flash("You are not authorized to delete this team.")
        return redirect(url_for('getIndex'))
    if request.method == 'POST':
        session.delete(team)
        session.commit()
        return redirect(url_for('getIndex'))
    else:
        user = login_session['username']
        return render_template(
            'delete.html', team_name=team_name, user=user
        )


@app.route('/catalog/teams/<team_name>/edit', methods=['GET', 'POST'])
@login_required
def editTeam(team_name):
    editedTeam = session.query(Team).filter_by(name=team_name).one()
    if editedTeam.user_id != login_session['user_id']:
        flash("You are not authorized to edit this team.")
        return redirect(url_for('getIndex'))
    country = session.query(Country).filter_by(
        id=editedTeam.country_id).one()
    countries = session.query(Country).all()
    if request.method == 'POST':
        if request.form['name']:
            name = request.form['name']
            if team_name != name and nameExists(name):
                flash("Please enter a different team. Team " +
                      name + " already exists.")
                return redirect(url_for('editTeam', team_name=team_name))
            editedTeam.name = name
        if request.form['description']:
            editedTeam.description = request.form['description']
        if request.form['country_id']:
            editedTeam.country_id = request.form['country_id']
        session.add(editedTeam)
        session.commit()
        return redirect(url_for('getIndex'))
    else:
        user = login_session['username']
        return render_template(
            'edit.html', team=editedTeam, country=country,
            countries=countries, user=user
        )


if __name__ == '__main__':
    app.secret_key = 'secret'
    app.debug = True
app.run(host='', port=5000)
