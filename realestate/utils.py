import re
import requests
from werkzeug.routing import BaseConverter


class ListConverter(BaseConverter):

    def to_python(self, value):
        return value.split(',')

    def to_url(self, values):
        return ','.join(BaseConverter.to_url(self, value)
                        for value in values)


def google_maps_url(origin, destination):
    url = "http://maps.googleapis.com/maps/api/distancematrix/json?"
    url += "origins={}".format(origin)
    url += "&destinations={}".format(destination)
    url += "&mode=driving"
    url += "&language=en-EN"
    url += "&sensor=false"
    return url


def extract_value_from_google_maps_api_request(request_json, required_info):
    try:
        return request_json['rows'][0]['elements'][0][required_info]['value']
    except (KeyError, IndexError):
        return None  # invalid format


def extract_text_from_google_maps_api_request(request_json, required_info):
    try:
        return request_json['rows'][0]['elements'][0][required_info]['text']
    except (KeyError, IndexError):
        return None  # invalid format


def google_maps_request(origin, destination, required_info):
    url = google_maps_url(origin, destination)

    try:
        request = requests.get(url)
    except requests.exceptions.ConnectionError:
        return None

    request_json = request.json()

    value = extract_value_from_google_maps_api_request(request_json)
    text = extract_text_from_google_maps_api_request(request_json)

    return value, text


def travel_time(origin, destination):
    return google_maps_request(origin, destination, 'duration')


def distance(origin, destination):
    return google_maps_request(origin, destination, 'distance')


def to_snakecase(name):
    try:
        return name.replace(" ", "_").lower()
    except AttributeError:
        return None


def camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def snake_to_camel(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

# TOTAL COST AND LOAN


def registration_rights(
    house_price,
    cadastral_income,
    nr_of_children,
    social_loan,
    social_house):
    return house_price * 0.05 if cadastral_income <= 745 else house_price * 0.125
    # requires further work


def total_cost(house_price):
    pass
