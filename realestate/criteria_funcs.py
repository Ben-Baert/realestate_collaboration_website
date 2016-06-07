import functools
import re
from .utils import travel_time

# DECORATORS


def register():
    registry = []
    def outer(name, dealbreaker=False, importance=5, applies_to=None):
        def registrar(func):
            if (any(item not in ['house', 'land'] for item in applies_to) or
               not applies_to):
                raise ValueError("""
                    Criterion must apply to land, house, or both
                    """)
            registry.append((func.__name__, name, dealbreaker,
                            10 if dealbreaker else importance,
                            applies_to))
            return func
        return registrar
    outer.all = registry
    return outer


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
        except (TypeError, AttributeError):
            return None, None
        if score is None:
            return None, None
        if score < 0:
            score = 0
        elif score > 10:
            score = 10
        return score, comment
    return inner

score_register = register()


# CRITERIA
@score_register(name="Time to Brussels by car",
                dealbreaker=False,
                importance=3,
                applies_to=['house', 'land'])
@score
def time_by_car_to_brussels(house):
    tt, comment = travel_time(house.address, "VUB, Brussel")
    return 10 - (tt - 3600)//360, comment


@score_register(name="Time to Leuven by car",
                dealbreaker=False,
                importance=5,
                applies_to=['house', 'land'])
@score
def time_by_car_to_leuven(house):
    tt, comment = travel_time(house.address, "Campus Arenberg, Heverlee")
    return 10 - (tt - 3600)//300, comment


@score_register(name="EPC score",
                dealbreaker=False,
                importance=6,
                applies_to=['house'])
@score
def epc(house):
    score = int(re.search("[0-9]+", house.epc).group(0))
    return 10 - (score - 150) // 60, house.epc


@score_register(name="Cadastral income under limit",
                dealbreaker=True,
                applies_to=['house'])
@score
def cadastral_income(house):
    return (int(int(house.cadastral_income.replace(".", "")[1:]) <= 745),
            house.cadastral_income)


@score_register(name="Price",
                dealbreaker=False,
                importance=10,
                applies_to=['house'])
@score
def house_price(house):
    return 10 - (house.price - 100000) // 7000, '€{0:,}'.format(house.price)


@score_register(name="Price",
                dealbreaker=False,
                importance=10,
                applies_to=['land'])
@score
def land_price(land):
    return 10 - (land.price - 20000) // 5000, '€{0:,}'.format(land.price)


@score_register(name="Year built",
                dealbreaker=False,
                importance=8,
                applies_to=['house'])
@score
def year(house):
    return 10 - (2016 - int(house.year)) // 4, house.year


@score_register(name="Spatial planning status of land",
                dealbreaker=True,
                applies_to=['house'])
@score
def spatial_planning(house):
    if not house.spatial_planning:
        return None, None
    return (int(house.spatial_planning != "Recreatiegebied"),
            house.spatial_planning)


@score_register(name="Heating",
                importance=6,
                dealbreaker=False,
                applies_to=['house'])
@score
def heating(house):
    if not house.heating:
        return None, None
    if house.heating == "Elektrisch":
        return 0, house.heating
    return 10, house.heating


@score_register(name="Building",
                dealbreaker=False,
                importance=8,
                applies_to=['house'])
@score
def building(house):
    if not house.building:
        return None, None
    if house.building == "Open":
        return 10, house.building
    return 0, house.building


@score_register(name="Price per m2",
                importance=9,
                applies_to=['house'])
@score
def house_price_per_m2(house):
    if house.price and house.total_area:
        price_per_m2 = house.price // house.total_area
        score = 10 - price_per_m2 // 15
        return score, '€{0:,}'.format(price_per_m2)


@score_register(name="Price per m2",
                importance=10,
                applies_to=['land'])
@score
def land_price_per_m2(land):
    if land.price and land.total_area:
        price_per_m2 = land.price // land.total_area
        score = 10 - price_per_m2 // 10
        return score, '€{0:,}'.format(price_per_m2)


@score_register(name="Total area",
                importance=8,
                applies_to=['house', 'land'])
@score
def total_area(house):
    return (house.total_area - 300) // 300, str(house.total_area) + "m2"


criteria_list = score_register.all
