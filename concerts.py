from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
import constants


ds_client = datastore.Client()
bp = Blueprint('concerts', __name__, url_prefix='/concerts')


def invalid_method_response(allowed_methods):
    res = make_response()
    res.headers.set("Allow", allowed_methods)
    res.status_code = 405
    return res


def create_concert():
    pass


def get_all_concerts():
    pass


def get_concert_with_id():
    pass


def edit_concert_with_id():
    pass


def delete_concert_with_id():
    pass


@bp.route('', methods=['POST', 'GET'])
def post_get_concerts():
    if request.method == 'POST':
        return create_concert()
    elif request.method == 'GET':
        return get_all_concerts()
    else:
        allowed_methods = 'POST, GET'
        return invalid_method_response(allowed_methods)


@bp.route('/<concert_id>', methods=['GET', 'PATCH', 'DELETE'])
def get_patch_delete_concert():
    if request.method == 'GET':
        return get_concert_with_id()
    elif request.method == 'PATCH':
        return edit_concert_with_id()
    elif request.method == 'DELETE':
        return delete_concert_with_id()
    else:
        allowed_methods = 'GET, PATCH, DELETE'
        return invalid_method_response(allowed_methods)
