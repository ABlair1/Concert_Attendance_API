from flask import Flask, render_template, request, redirect, url_for
from google.auth import jwt
from google.cloud import datastore
import google.oauth2.credentials
import google_auth_oauthlib.flow
import bands
import concerts
import constants
import random
import string
import users


app = Flask(__name__)
ds_client = datastore.Client()
app.register_blueprint(bands.bp)
# app.register_blueprint(concerts.bp)
app.register_blueprint(users.bp)


def store_state(state):
    new_state = datastore.entity.Entity(key=ds_client.key(constants.state))
    new_state.update({'value': state})
    ds_client.put(new_state)


def generate_new_state():
    state = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
    store_state(state)
    return state


def validate_state(state):
    query = ds_client.query(kind=constants.state)
    state_list = list(query.fetch())
    for s in state_list:
        if s['value'] == state:
            return True
    return False


def get_jwt_token(state):
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=['https://www.googleapis.com/auth/userinfo.profile'],
        state=state
    )
    flow.redirect_uri = url_for('home', _external=True)
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    jwt_token = flow.credentials.id_token
    return jwt_token


def get_user_info(jwt_token):
    decoded_jwt = jwt.decode(jwt_token, verify=False)
    user_info = {
        'f_name': decoded_jwt['given_name'],
        'l_name': decoded_jwt['family_name'],
        'auth_id': decoded_jwt['sub']
    }
    return user_info


def update_user(user, user_info):
        user.update({
        'f_name': user_info['f_name'], 
        'l_name': user_info['l_name'], 
        'auth_id': user_info['auth_id'],
        'concerts': []
    })


def store_user(user_info):
    query = ds_client.query(kind=constants.user)
    user_list = list(query.fetch())
    for user in user_list:
        if user['auth_id'] == user_info['auth_id']:
            return
    new_user = datastore.entity.Entity(key=ds_client.key(constants.user))
    update_user(new_user, user_info)
    ds_client.put(new_user)


@app.route('/')
def home():
    if 'code' not in request.args:  # user not authenticated
        return render_template('welcome.html')
    state = request.args.get('state')
    if not validate_state(state):
        return ('Error: Invalid state credential', 401)
    jwt_token = get_jwt_token(state)
    user_info = get_user_info(jwt_token)
    store_user(user_info)  # user entity created if not already in datastore
    return render_template('user_info.html',
        f_name=user_info['f_name'],
        l_name=user_info['l_name'],
        auth_id=user_info['auth_id'],
        jwt_token=jwt_token
    )


@app.route('/oauth')
def oauth_request():
    new_state = generate_new_state()
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=['https://www.googleapis.com/auth/userinfo.profile']
    )
    flow.redirect_uri = url_for('home', _external=True)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        state=new_state,
        include_granted_scopes='true'
    )
    return redirect(authorization_url)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
