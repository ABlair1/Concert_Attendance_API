from flask import Blueprint, request, make_response
from google.cloud import datastore
import json
import constants


ds_client = datastore.Client()
bp = Blueprint('concerts', __name__, url_prefix='/concerts')
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


def validate_concert_id(concert):
    err = {"Error": "No concert with this concert_id exists"}
    if concert is None:
        res = make_response(json.dumps(err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 404
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


def validate_date_format(date):
    err = {"Error": "Date must be in format MM-DD-YYYY and a real date that exists"}
    month_days = {
        1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
    }
    date_err = False
    if type(date) != str:
        date_err = True
    date_list = date.split("-")
    if len(date_list) != 3:
        date_err = True
    else:
        month = int(date_list[0])
        day = int(date_list[1])
        year = int(date_list[2])
        if year % 4 == 0:
            month_days[2] += 1
        if year < 0 or year > 9999:
            date_err = True
        if month < 1 or month > 12:
            date_err = True
        if day < 1 or day > month_days[month]:
            date_err = True
    if date_err:
        res = make_response(json.dumps(err))
        res.headers.set("Content-type", "application/json")
        res.status_code = 400
        return res
    return None


def validate_concert_attribute_keys(req_body):
    allowed = ["venue", "address", "date", "band"]
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


def validate_concert_attributes(req_body):
    required = ["venue", "address", "date", "band"]
    attr_err = {"Error": "The request object is missing at least one of the required attributes"}
    for attr in required:
        if attr not in req_body:
            res = make_response(json.dumps(attr_err))
            res.headers.set("Content-type", "application/json")
            res.status_code = 400
            return res
    key_err = validate_concert_attribute_keys(req_body)
    if key_err is not None:
        return key_err
    date_err = validate_date_format(req_body["date"])
    if date_err is not None:
        return date_err
    band = ds_client.get(key=ds_client.key(constants.band, int(req_body["band"])))
    band_err = validate_band_id(band)
    if band_err is not None:
        return band_err
    return None


def add_concert_to_band(concert_id, band_id):
    band = ds_client.get(key=ds_client.key(constants.band, int(band_id)))
    band["concerts"].append({"id": concert_id})
    ds_client.put(band)


def remove_concert_from_band(concert_id, band_id):
    band = ds_client.get(key=ds_client.key(constants.band, int(band_id)))
    for concert in band["concerts"]:
        if concert["id"] == concert_id:
            band["concerts"].remove(concert)
    ds_client.put(band)


def update_new_concert(concert, req_body):
    updates = {}
    updates["venue"] = req_body["venue"]
    updates["address"] = req_body["address"]
    updates["date"] = req_body["date"]
    updates["band"] = {"id": req_body["band"]}
    concert.update(updates)


def update_concert_details(concert, req_body):
    updates = {}
    if "venue" in req_body:
        updates["venue"] = req_body["venue"]
    if "address" in req_body:
        updates["address"] = req_body["address"]
    if "date" in req_body:
        updates["date"] = req_body["date"]
    if "band" in req_body and req_body["band"] != concert["band"]["id"]:
        updates["band"] = {"id": req_body["band"]}
        add_concert_to_band(concert.key.id, req_body["band"])
        remove_concert_from_band(concert.key.id, concert["band"]["id"])
    concert.update(updates)


def create_concert(req):
    # Validate request headers
    content_error = validate_content_header_json(req.headers)
    if content_error is not None:
        return content_error
    accept_error = validate_accept_header_json(req.headers)
    if accept_error is not None:
        return accept_error
    # Validate request body
    req_body = req.get_json()
    attr_err = validate_concert_attributes(req_body)
    if attr_err is not None:
        return attr_err
    # Create concert in datastore and send response with result
    new_concert = datastore.entity.Entity(key=ds_client.key(constants.concert))
    update_new_concert(new_concert, req_body)
    ds_client.put(new_concert)
    add_concert_to_band(new_concert.key.id, new_concert["band"]["id"])
    new_concert["id"] = new_concert.key.id
    new_concert["self"] = req.base_url + "/" + str(new_concert.key.id)
    new_concert["band"]["self"] = req.base_url[:-8] + "bands/" + str(new_concert["band"]["id"])
    res = make_response(json.dumps(new_concert))
    res.headers.set("Content-type", "application/json")
    res.status_code = 201
    return res


def get_all_concerts(req):
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
        return create_concert(request)
    elif request.method == 'GET':
        return get_all_concerts(request)
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
