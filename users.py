from flask import Blueprint, request, make_response
from google.auth.transport import requests as grequests
from google.cloud import datastore
from google.oauth2 import id_token
import json
import constants


ds_client = datastore.Client()
bp = Blueprint('users', __name__, url_prefix='/users')

with open('client_secret.json', 'r') as client_secret_json:
    data = client_secret_json.read()
client_properties = json.loads(data)
client_id = client_properties['web']['client_id']


#######################################################################
# Functions
#######################################################################
def invalid_method_response(allowed_methods):
    res = make_response()
    res.headers.set("Allow", allowed_methods)
    res.status_code = 405
    return res


def validate_accept_header_json(req_headers):
    accept_err = {"Error": "Requests must accept response Content-type of application/json"}
    accept_headers = req_headers.get("Accept").replace(";", ",")
    accept_headers = accept_headers.split(",")
    for header in accept_headers:
        header = header.strip()
    if "application/json" not in accept_headers and "*/*" not in accept_headers:
        res = make_response(json.dumps(accept_err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 406
        return res
    return None


def validate_content_header_json(req_headers):
    content_err = {"Error": "Request Content-type must be application/json"}
    content_headers = req_headers.get("Content-type").replace(";", ",")
    content_headers = content_headers.split(",")
    for header in content_headers:
        header = header.strip()
    if "application/json" not in content_headers:
        res = make_response(json.dumps(content_err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 415
        return res
    return None


def validate_user_id(user):
    err = {"Error": "No user with this user_id exists"}
    if user is None:
        res = make_response(json.dumps(err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 404
        return res
    return None


def validate_concert_ids(concert_id_list):
    err = {"Error": "One or more concert_id values does not exist"}
    for concert_id in concert_id_list:
        concert = ds_client.get(key=ds_client.key(constants.concert, int(concert_id)))
        if concert is None:
            res = make_response(json.dumps(err))
            res.headers.set("Content-type", "application/json")
            res.status_code = 404
            return res
    return None


def get_id_from_jwt(req):
    if 'Authorization' not in req.headers:
        return None
    auth_header = req.headers['Authorization'].split()
    if len(auth_header) <2 or auth_header[0] != 'Bearer':
        return None
    jwt_token = auth_header[1]
    try:
        id_info = id_token.verify_oauth2_token(jwt_token, grequests.Request(), client_id)
        user_id = id_info['sub']
    except:
        return None
    return user_id


def validate_user_permission(user_id, req):
    token_err = {"Error": "This resource is protected and the user is not authorized"}
    token_user_id = get_id_from_jwt(req)
    if token_user_id != user_id:
        res = make_response(json.dumps(token_err))
        res.headers.set("Content-type", "application/json")
        if token_user_id is None:
            res.status_code = 401
        else:
            res.status_code = 403
        return res
    return None


def validate_user_req_body(req_body):
    body_err = {"Error": "The request body may only contain the concerts attribute"}
    if len(req_body) != 1 or "concerts" not in req_body:
        res = make_response(json.dumps(body_err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 404
        return res
    return None


def add_concert_to_user(user_id, req):
    # Validate request headers, request body, and user_id from path
    accept_err = validate_accept_header_json(req.headers)
    if accept_err is not None:
        return accept_err
    content_err = validate_content_header_json(req.headers)
    if content_err is not None:
        return content_err
    query = ds_client.query(kind=constants.user)
    user_list = list(query.fetch())
    user = None
    for user_entity in user_list:
        if user_entity["user_id"] == user_id:
            user = user_entity
            break
    user_id_err = validate_user_id(user)
    if user_id_err is not None:
        return user_id_err
    auth_err = validate_user_permission(user_id, req)
    if auth_err is not None:
        return auth_err
    req_body = req.get_json()
    req_body_err = validate_user_req_body(req_body)
    if req_body_err is not None:
        return req_body_err
    concert_id_err = validate_concert_ids(req_body["concerts"])
    if concert_id_err is not None:
        return concert_id_err
    # Insert concert_id(s) into user concerts and return result
    current_user_concerts = []
    for concert in user["concerts"]:
        current_user_concerts.append(concert["id"])
    for concert_id in req_body["concerts"]:
        if concert_id not in current_user_concerts:
            user["concerts"].append({"id": concert_id})
    ds_client.put(user)
    user.pop("f_name", None)
    user.pop("l_name", None)
    user.pop("user_id", None)
    for concert in user["concerts"]:
        concert["self"] = req.base_url[:-36] + "concerts/" + str(concert["id"])
    res = make_response(json.dumps(user))
    res.headers.set("Content-type", "application/json")
    res.status_code = 201
    return res


def get_user_concerts(user_id, req):
    # Validate request headers
    accept_err = validate_accept_header_json(req.headers)
    if accept_err is not None:
        return accept_err
    auth_err = validate_user_permission(user_id, req)
    if auth_err is not None:
        return auth_err
    # Retrieve and return list of user concerts


def remove_concert_from_user(user_id, concert_id, req):
    # Validate request headers
    accept_err = validate_accept_header_json(req.headers)
    if accept_err is not None:
        return accept_err
    auth_err = validate_user_permission(user_id, req)
    if auth_err is not None:
        return auth_err
    # Remove concert_id from list of user concerts


def get_all_users(req):
    # Validate request headers
    accept_err = validate_accept_header_json(req.headers)
    if accept_err is not None:
        return accept_err
    # Retrieve and return list of all users (omit concerts attribute)
    query = ds_client.query(kind=constants.user)
    user_list = list(query.fetch())
    for user in user_list:
        user.pop("concerts", None)
    res = make_response(json.dumps(user_list))
    res.headers.set("Content-type", "application/json")
    res.status_code = 200
    return res


#######################################################################
# Route Handlers
#######################################################################
@bp.route('', methods=['GET'])
def get_users():
    if request.method == 'GET':
        return get_all_users(request)
    else:
        allowed_methods = 'GET'
        return invalid_method_response(allowed_methods)


@bp.route('/<user_id>/concerts', methods=['POST', 'GET'])
def post_get_user_concerts(user_id):
    if request.method == 'POST':
        return add_concert_to_user(user_id, request)
    elif request.method == 'GET':
        return get_user_concerts(user_id, request)
    else:
        allowed_methods = 'POST, GET'
        return invalid_method_response(allowed_methods)


@bp.route('/<user_id>/concerts/<concert_id>', methods=['DELETE'])
def delete_user_concert(user_id, concert_id):
    if request.method == 'DELETE':
        return remove_concert_from_user(user_id, concert_id, request)
    else:
        allowed_methods = 'DELETE'
        return invalid_method_response(allowed_methods)
