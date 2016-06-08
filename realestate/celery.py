import json
from peewee import IntegrityError
from celery import Celery, Task
from realestate import app
from datetime import timedelta
from flask import has_request_context, request, make_response
from .models import (Realestate,
                     RealestateInformationCategory,
                     RealestateInformation,
                     RealestateCriterion,
                     RealestateCriterionScore,
                     Feature,
                     RealestateFeature,
                     User,
                     database)


celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


@celery.task
@database.atomic()
def add_from_json(r):
    r = json.loads(r)
    urls = [realestate.realo_url for realestate in Realestate.select()]
    if r["realo_url"] in urls:
        return
    try:
        inhabitable_area, total_area = r["area"]
        lat, lng = r["coordinates"]
        realestate = Realestate.create(
                added_on=r["added_on"],
                realestate_type=r["realestate_type"],
                seller=r["seller"],
                address=r["address"],
                inhabitable_area=inhabitable_area,
                total_area=total_area,
                lat=lat,
                lng=lng,
                description=r["description"],
                price=r["price"],
                realo_url=r["realo_url"],
                thumbnail_pictures=r["thumbnail_pictures"],
                main_pictures=r["main_pictures"],
                )
        print(realestate.realo_url + " added.")
    except IntegrityError:
        return

    for information in r["information"]:
        category, _ = (RealestateInformationCategory
                       .get_or_create(_realo_name=information[0]))

        RealestateInformation.create(
            realestate=realestate,
            category=category,
            value=information[1])

    for criterion in RealestateCriterion.select():
        RealestateCriterionScore.create(criterion=criterion,
                                        realestate=realestate)

    for feature in r["features"]:
        feature, _ = Feature.get_or_create(name=feature)
        RealestateFeature.create(feature=feature, realestate=realestate)


@celery.task
@database.atomic()
def prepare_caches():
    for user in User.select():
        cached_queue = sorted(Realestate.full_queue(user),
                              key=lambda x: (-x.score, -x._score))
        for _ in range(len(user.cached_queue)):  # empty current queue; REFACTOR!
            user.cached_queue.pop()
        #print(user.cached_queue)
        user.cached_queue.extend([x._id for x in cached_queue])  # add new items to queue

