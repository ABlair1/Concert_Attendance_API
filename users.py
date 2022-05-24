from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
import constants


ds_client = datastore.Client()
bp = Blueprint('users', __name__, url_prefix='/users')


def invalid_method_response(allowed_methods):
    res = make_response()
    res.headers.set("Allow", allowed_methods)
    res.status_code = 405
    return res


def validate_accept_header_json(req_headers):
    accept_err = {"Error": "Requests must accept response Content-type of application/json"}
    accept_headers = req_headers.get("Accept").split(",")
    for header in accept_headers:
        header = header.strip()
    if "application/json" not in accept_headers and "*/*" not in accept_headers:
        res = make_response(json.dumps(accept_err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 406
        return res
    return None


def get_all_users(req):
    # Validate request headers
    accept_error = validate_accept_header_json(req.headers)
    if accept_error is not None:
        return accept_error
    # Retrieve and return list of all users (omit concerts attribute)
    query = ds_client.query(kind=constants.user)
    user_list = list(query.fetch())
    res = make_response(json.dumps(user_list))
    res.headers.set("Content-type", "application/json")
    res.status_code = 200
    return res


@bp.route('', methods=['GET'])
def get_users():
    if request.method == 'GET':
        return get_all_users(request)
    else:
        allowed_methods = 'GET'
        return invalid_method_response(allowed_methods)
