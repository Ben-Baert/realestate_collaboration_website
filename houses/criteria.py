import functools
from .utils import travel_time

# GENERIC HELPERS



# DECORATORS


def register():
    registry = []
    def outer(name, dealbreaker=False, importance=5):
        def registrar(func):
            registry.append((func.__name__, name, dealbreaker, 10 if dealbreaker else importance))
            return func
        return registrar
    outer.all = registry
    return outer

score_register = register()

def score(func):
    """
    Decorator function that makes sure
    that scores are always in the 0-10
    range.
    """
    @functools.wraps(func)
    def inner(*args, **kwargs):
        try:
            score, comment = func(*args, **kwargs)
        except (TypeError, AttributeError) as e:
            return None, None
        if score < 0:
            score = 0
        elif score > 10:
            score = 10
        return score, comment
    return inner


# CRITERIA
@score_register(name="Time to Brussels by car", dealbreaker=False, importance=3)
@score
def time_by_car_to_brussels(house):
    tt, comment = travel_time(house.address, "VUB, Brussel")
    return 10 - (tt - 3600)//360, comment


@score_register(name="Time to Leuven by car", dealbreaker=False, importance=5)
@score
def time_by_car_to_leuven(house):
    tt, comment = travel_time(house.address, "Campus Arenberg, Heverlee")
    return 10 - (tt - 3600)//180, comment


@score_register(name="EPC score", dealbreaker=False, importance=6)
@score
def epc(house):
    return 10 - (int(house.epc[:3]) - 150) // 60, house.epc


@score_register(name="Cadastral income under limit", dealbreaker=True)
@score
def cadastral_income(house):
    return int(int(house.cadastral_income[1:]) < 745), house.cadastral_income


@score_register(name="Price", dealbreaker=False, importance=10)
@score
def price(house):
    return 10 - (house.price - 100000) // 7000, '€{0:,}'.format(house.price)


@score_register(name="Year built", dealbreaker=False, importance=8)
@score
def year(house):
    return 10 - (2016 - int(house.year)) // 4, house.year


@score_register(name="Spatial planning status of land", dealbreaker=True)
@score
def spatial_planning(house):
    return house.spatial_planning != "Recreatiegebied", house.spatial_planning


@score_register(name="Heating", dealbreaker=True)
@score
def heating(house):
    return int(house.heating != "Elektrisch"), house.heating

@score_register(name="Building", importance=8)
@score
def building(house):
    if house.building == "Open":
        return 10
    return 0
criteria_list = score_register.all
