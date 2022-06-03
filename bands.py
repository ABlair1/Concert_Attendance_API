from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
import constants


ds_client = datastore.Client()
bp = Blueprint('bands', __name__, url_prefix='/bands')
pg_limit = 5


def invalid_method_response(allowed_methods):
    res = make_response()
    res.headers.set("Allow", allowed_methods)
    res.status_code = 405
    return res


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


def validate_band_id(band):
    err = {"Error": "No band with this band_id exists"}
    if band is None:
        res = make_response(json.dumps(err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 404
        return res
    return None


def validate_band_attribute_keys(req_body):
    allowed = ["name", "genre", "members"]
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
    if "name" not in req_body or "genre" not in req_body or "members" not in req_body:
        res = make_response(json.dumps(attr_err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 400
        return res
    key_err = validate_band_attribute_keys(req_body)
    if key_err is not None:
        return key_err
    return None


def update_new_band(band, req_body):
    updates = {}
    updates["name"] = req_body["name"]
    updates["genre"] = req_body["genre"]
    updates["members"] = req_body["members"]
    updates["concerts"] = []
    band.update(updates)


def update_band_details(band, req_body):
    updates = {}
    if "name" in req_body:
        updates["name"] = req_body["name"]
    if "genre" in req_body:
        updates["genre"] = req_body["genre"]
    if "members" in req_body:
        updates["members"] = req_body["members"]
    band.update(updates)


def update_band_concerts():
    pass


def create_band(req):
    # Validate request headers
    content_error = validate_content_header_json(req.headers)
    if content_error is not None:
        return content_error
    accept_error = validate_accept_header_json(req.headers)
    if accept_error is not None:
        return accept_error
    # Validate request body
    req_body = req.get_json()
    attr_err = validate_band_attributes(req_body)
    if attr_err is not None:
        return attr_err
    # Create band in datastore and send response with result
    new_band = datastore.entity.Entity(key=ds_client.key(constants.band))
    update_new_band(new_band, req_body)
    ds_client.put(new_band)
    new_band["id"] = new_band.key.id
    new_band["self"] = req.base_url + "/" + str(new_band.key.id)
    res = make_response(json.dumps(new_band))
    res.headers.set("Content-type", "application/json")
    res.status_code = 201
    return res


def get_all_bands(req):
    # Validate request headers
    accept_error = validate_accept_header_json(req.headers)
    if accept_error is not None:
        return accept_error
    # Retrieve and return list of all bands
    query = ds_client.query(kind=constants.band)
    q_limit = int(req.args.get("limit", str(pg_limit)))
    q_offset = int(req.args.get("offset", "0"))
    q_result = query.fetch(limit=q_limit, offset=q_offset)
    band_list = {"bands": list(next(q_result.pages))}
    for band in band_list["bands"]:
        band["id"] = band.key.id
        band["self"] = req.base_url + "/" + str(band.key.id)
        for concert in band["concerts"]:
            concert["self"] = req.base_url[:-5] + "concerts/" + str(concert["id"])
    band_list["self"] = f"{req.base_url}?limit={q_limit}&offset={q_offset}"
    if q_result.next_page_token:
        band_list["next"] = f"{req.base_url}?limit={q_limit}&offset={q_limit+q_offset}"
    res = make_response(json.dumps(band_list))
    res.headers.set("Content-type", "application/json")
    res.status_code = 200
    return res


def get_band_with_id(band_id, req):
    band = ds_client.get(key=ds_client.key(constants.band, int(band_id)))
    id_error = validate_band_id(band)
    if id_error is not None:
        return id_error
    band["id"] = band.key.id
    band["self"] = req.base_url
    for concert in band["concerts"]:
        concert["self"] = req.base_url[:-22] + "concerts/" + str(concert["id"])
    res = make_response(json.dumps(band))
    res.headers.set("Content-type", "application/json")
    res.status_code = 200
    return res


def edit_band_with_id(band_id, req):
    # Validate request headers
    content_error = validate_content_header_json(req.headers)
    if content_error is not None:
        return content_error
    accept_error = validate_accept_header_json(req.headers)
    if accept_error is not None:
        return accept_error
    # Validate band_id and request body
    band = ds_client.get(key=ds_client.key(constants.band, int(band_id)))
    id_error = validate_band_id(band)
    if id_error is not None:
        return id_error
    req_body = req.get_json()
    key_err = validate_band_attribute_keys(req_body)
    if key_err is not None:
        return key_err
    # Update band entity and send response with result
    update_band_details(band, req_body)
    ds_client.put(band)
    band["id"] = band.key.id
    band["self"] = req.base_url
    for concert in band["concerts"]:
        concert["self"] = req.base_url[:-22] + "concerts/" + str(concert["id"])
    res = make_response(json.dumps(band))
    res.headers.set("Content-type", "application/json")
    res.status_code = 200
    return res


def delete_band_with_id(band_id, req):
    # # Validate band id
    # band = ds_client.get(key=ds_client.key(constants.band, int(band_id)))
    # id_error = validate_band_id(band)
    # if id_error is not None:
    #     return id_error
    # # Remove associated concerts from users and delete concerts
    # concert_list = 
    # # Delete band entity
    pass


@bp.route('', methods=['POST', 'GET'])
def post_get_bands():
    if request.method == 'POST':
        return create_band(request)
    elif request.method == 'GET':
        return get_all_bands(request)
    else:
        allowed_methods = 'POST, GET'
        return invalid_method_response(allowed_methods)


@bp.route('/<band_id>', methods=['GET', 'PATCH', 'DELETE'])
def get_patch_delete_bands(band_id):
    if request.method == 'GET':
        return get_band_with_id(band_id, request)
    elif request.method == 'PATCH':
        return edit_band_with_id(band_id, request)
    elif request.method == 'DELETE':
        return delete_band_with_id(band_id, request)
    else:
        allowed_methods = 'GET, PATCH, DELETE'
        return invalid_method_response(allowed_methods)
