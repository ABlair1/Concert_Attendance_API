from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
import constants


ds_client = datastore.Client()
bp = Blueprint('bands', __name__, url_prefix='/bands')


def invalid_method_response(allowed_methods):
    res = make_response()
    res.headers.set("Allow", allowed_methods)
    res.status_code = 405
    return res


def create_band():
    pass


def get_all_bands():
    pass


def get_band_with_id():
    pass


def edit_band_with_id():
    pass


def delete_band_with_id():
    pass


@bp.route('', methods=['POST', 'GET'])
def post_get_bands():
    if request.method == 'POST':
        return create_band()
    elif request.method == 'GET':
        return get_all_bands()
    else:
        allowed_methods = 'POST, GET'
        return invalid_method_response(allowed_methods)


@bp.route('/<band_id>', methods=['GET', 'PATCH', 'DELETE'])
def get_patch_delete_bands():
    if request.method == 'GET':
        return get_band_with_id()
    elif request.method == 'PATCH':
        return edit_band_with_id()
    elif request.method == 'DELETE':
        return delete_band_with_id()
    else:
        allowed_methods = 'GET, PATCH, DELETE'
        return invalid_method_response(allowed_methods)
