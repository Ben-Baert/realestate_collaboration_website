from peewee import IntegrityError
from .app import celery
from .models import (Realestate,
                     RealestateInformationCategory,
                     RealestateInformation, 
                     RealestateCriterion,
                     RealestateCriterionScore,
                     Feature,
                     RealestateFeature,
                     Notification,
                     database)
from houses.scrapers.realo import Realo, RealoSearch



@celery.task
def generate_feed():
    urls = (realestate.url for realestate in Realestate.select())
    with RealoSearch() as search:
        for item in search.houses_urls():
            if item not in urls:
                add_realo_realestate.delay(item)


@celery.task
@database.atomic()
def add_realo_realestate(url):
    with Realo(url) as realo_realestate:
        print(url)
        lat, lng = realo_realestate.lat_lng()
        inhabitable_area, total_area = realo_realestate.area()
        try:
            realestate = Realestate.create(
                    added_on=realo_realestate.added_on(),
                    realestate_type=realo_realestate.realestate_type(),
                    seller=realo_realestate.seller(),
                    address=realo_realestate.address(),
                    inhabitable_area=inhabitable_area,
                    total_area=total_area,
                    lat=lat,
                    lng=lng,
                    description=realo_realestate.description(),
                    price=realo_realestate.price(),
                    realo_url=url,
                    thumbnail_pictures=realo_realestate.thumbnail_pictures(),
                    main_pictures=realo_realestate.main_pictures(),
                    )
        except IntegrityError:
            return

        for information in realo_realestate.information():
            category, _ = (RealestateInformationCategory
                           .get_or_create(_realo_name=information[0]))

            RealestateInformation.create(
                realestate=realestate,
                category=category,
                value=information[1])

        for criterion in RealestateCriterion.select():
            RealestateCriterionScore.create(criterion=criterion, realestate=realestate)

        for feature in realo_realestate.features():
            feature, _ = Feature.get_or_create(name=feature)
            RealestateFeature.create(feature=feature, realestate=realestate)

        #Notification.create(realestate.realestate_type, realestate)