import requests
import functools

__all__ = ['cadastral_income']

# GENERIC HELPERS

def google_maps_url(origin, destination):
    return "http://maps.googleapis.com/maps/api/distancematrix/json?origins={}&destinations={}&mode=driving&language=en-EN&sensor=false".format(origin, destination)


def google_maps_request(origin, destination, t, raw=True):
    url = google_maps_url(origin, destination)
    r = requests.get(url).json()
    if raw:
        return r['rows'][0]['elements'][0][t]['value']
    return r['rows'][0]['elements'][0][t]['text']


def travel_time(origin, destination):
    return google_maps_request(origin, destination, 'duration')


def distance(origin, destination):
    return google_maps_request(origin, destination, 'distance')


def score(func):
    """
    Decorator function that makes sure
    that scores are always in the 0-10
    range.
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        result = func(*args, **kwargs)
        print(func.__name__ + " was called!")
        if result < 0:
            return 0
        elif result > 10:
            return 10
        return result
    return inner


# CRITERIA
@score
def time_by_car_to_brussels(house):
    tt = travel_time(house.address, "VUB, Brussel")
    if tt <= 3600:
        return 10
    elif tt >= 7200:
        return 0


@score
def time_by_car_to_leuven(house):
    return travel_time(house.address, "Campus Arenberg, Heverlee", )


@score
def good_epc(house):
    if not house.epc:
        return None
    return 10 - house.epic // 60


@score
def cadastral_income(house):
    return int(int(house.cadastral_income[1:]) < 745)
