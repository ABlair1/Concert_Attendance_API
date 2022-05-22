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


def get_all_users():
    query = ds_client.query(kind=constants.user)
    user_list = list(query.fetch())
    res = make_response(json.dumps(user_list))
    res.headers.set("Content-type", "application/json")
    res.status_code = 200
    return res


@bp.route('', methods=['GET'])
def get_users():
    if request.method == 'GET':
        return get_all_users()
    else:
        allowed_methods = 'GET'
        return invalid_method_response(allowed_methods)
