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


def validate_content_header_json(req_headers):
    content_err = {"Error": "Request Content-type must be application/json"}
    content_headers = req_headers.get("Content-type").split(", ")
    if "application/json" not in content_headers:
        res = make_response(json.dumps(content_err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 415
        return res
    return None

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


def validate_band_id(band):
    err = {"Error": "No band with this band_id exists"}
    if band is None:
        res = make_response(json.dumps(err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 404
        return res
    return None

def validate_band_attribute_keys(req_body):
    allowed = ["name", "type", "length"]
    err = {"Error": "The request object includes additional attributes which are not permitted"}
    if len(req_body) > len(allowed):
        res = make_response(json.dumps(err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 400
        return res
    req_attributes = list(req_body.keys())
    for attribute in req_attributes:
        if attribute not in allowed:
            res = make_response(json.dumps(err))
            res.headers.set("Content-type", "application/json")
            res.status_code = 400
            return res
    return None

def validate_band_attributes(req_body):
    attr_err = {"Error": "The request object is missing at least one of the required attributes"}
    if "name" not in req_body or "type" not in req_body or "length" not in req_body:
        res = make_response(json.dumps(attr_err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 400
        return res
    key_err = validate_band_attribute_keys(req_body)
    if key_err is not None:
        return key_err
    return None


def update_band(band, req_body):
    updates = {}
    if "name" in req_body:
        updates["name"] = req_body["name"]
    if "type" in req_body:
        updates["type"] = req_body["type"]
    if "length" in req_body:
        updates["length"] = req_body["length"]
    band.update(updates)


def create_band(req):
    content_error = validate_content_header_json(req.headers)
    if content_error is not None:
        return content_error
    accept_error = validate_accept_header_json(req.headers)
    if accept_error is not None:
        return accept_error
    req_body = req.get_json()
    attr_err = validate_band_attributes(req_body)
    if attr_err is not None:
        return attr_err
    new_band = datastore.entity.Entity(key=ds_client.key(constants.band))
    update_band(new_band, req_body)
    ds_client.put(new_band)
    new_band["id"] = new_band.key.id
    new_band["self"] = req.base_url + "/" + str(new_band.key.id)
    res = make_response(json.dumps(new_band))
    res.headers.set("Content-type", "application/json")
    res.status_code = 201
    return res


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
