from flask import Markup
from operator import attrgetter
from realestate import app


@app.template_filter('information')
def informationfilter(s):
    return s or "?"


@app.template_filter('dealbreakerscore')
def dealbreakerscore(s):
    if s == 0:
        html = "X"
    elif s == 1:
        html = "OK"
    else:
        html = "?"
    return Markup(html)


@app.template_filter('price')
def price(s):
    return '€{0:,}'.format(s)


@app.template_filter('area')
def area(s):
    return Markup('{0:,}m<sup>2</sup>'.format(s))


@app.template_filter('multisort')
def sort_multi(L, *operators):
    return sorted(L, key=attrgetter(*operators))


@app.template_filter('date')
def date(d):
    try:
        return d.strftime("%d/%m/%Y")
    except AttributeError:
        return "?"
