import re
import requests


def google_maps_url(origin, destination):
    return "http://maps.googleapis.com/maps/api/distancematrix/json?origins={}&destinations={}&mode=driving&language=en-EN&sensor=false".format(origin, destination)


def google_maps_request(origin, destination, t):
    url = google_maps_url(origin, destination)
    r = requests.get(url)
    print(r.request.url)
    r = r.json()
    return r['rows'][0]['elements'][0][t]['value'], r['rows'][0]['elements'][0][t]['text']


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


def registration_rights(house_price, cadastral_income, nr_of_children, social_loan, social_house):
    return house_price * 0.05 if cadastral_income <= 745 else house_price * 0.125

def total_cost(house_price):
    pass