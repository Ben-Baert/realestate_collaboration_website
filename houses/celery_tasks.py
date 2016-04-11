from peewee import IntegrityError
from .app import celery
from .models import (House,
                     HouseInformationCategory,
                     HouseInformation, Criterion,
                     CriterionScore,
                     Feature,
                     HouseFeature,
                     Notification)
from houses.scrapers.realo import Realo, RealoSearch

@celery.task
def generate_feed():
    with RealoSearch() as search:
        for item in search.urls():
            add_realo_house.delay(item)


@celery.task
def add_realo_house(url):
    #with app.app_context():
    with Realo(url) as realo_house:
        lat, lng = realo_house.lat_lng()
        inhabitable_area, total_area = realo_house.area()
        try:
            house = House.create(
                    added_on=realo_house.added_on(),
                    seller=realo_house.seller(),
                    address=realo_house.address(),
                    inhabitable_area=inhabitable_area,
                    total_area=total_area,
                    lat=lat,
                    lng=lng,
                    description=realo_house.description(),
                    price=realo_house.price(),
                    realo_url=url,
                    thumbnail_pictures=realo_house.thumbnail_pictures(),
                    main_pictures=realo_house.main_pictures(),
                    )
        except IntegrityError:
            return

        for information in realo_house.information():
            category, _ = (HouseInformationCategory
                           .get_or_create(_realo_name=information[0]))
            HouseInformation.create(
                house=house,
                category=category,
                value=information[1])

        for criterion in Criterion.select():
            CriterionScore.create(criterion=criterion, house=house)

        for feature in realo_house.features():
            feature, _ = Feature.get_or_create(name=feature)
            HouseFeature.create(feature=feature, house=house)

        Notification.create('house', house)