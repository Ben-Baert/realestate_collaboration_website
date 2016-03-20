from walrus import *
from bcrypt import hashpw, gensalt
database = PostgreSqlDatabase()

class BaseModel(Model):
    class Meta:
        database = database

class User(BaseModel):
    username = CharField(min_length=3,
                         max_length=30)
    password = CharField(min_length=6)
    email = CharField()
    
    def set_password(self, plaintext_password):
        self.password = hashpw(plaintext_password, gensalt())

    def verify_password(self, plaintext_password):
        return hashpw(self.password, hashpw(plaintext_password, gensalt()))


class Criterion(BaseModel):
    title = CharField(max_length=30)
    description = TextField()
    dealbreaker = BooleanField(default=False) # if set to True, any house with score of 0
                                              # on this criterion will be rejected
    importance = IntegerField() # range 0-10


class Seller(BaseModel):
    name = CharField(max_length=30)
    telephone_number = CharField()
    real_estate_agent = BooleanField()


class House(BaseModel):
    title = CharField(max_length=50)
    seller = ForeignKeyField(Seller, related_name='houses')
    
    street = CharField()
    house_nr = CharField()
    postal_code = CharField()
    town = CharField()
    lat = FloatField()
    lng = FloatField()
    photos = ListField()

    contacted = BooleanField(default=False)
    visited = BooleanField(default=False)
    inhabitable_area = IntegerField() # in square meters
    garden_area = IntegerField() # 0 if no garden
    surface_area = IntegerField() # square meters
    garage_surface = IntegerField() # 0 if no garage
#    proximity_to_highway = IntegerField() # in meters
#    proximity_to_train_station = IntegerField() # in meters
#    travel_time_to_leuven_by_car = IntegerField() # in minutes
#    travel_time_to_leuven_by_pt = IntegerField() # in minutes
#    travel_time_to_brussels_by_car = IntegerField() # in minutes
#    proximity_of_forest = IntegerField()

class CriterionScore(BaseModel):
    criterion = ForeignKeyField(Criterion, related_name='houses')
    house = ForeignKeyField(House, related_name='criterion_scores')
    score = IntegerField() # range 0-10
    comment = TextField()

class Appointment(BaseModel):
    house = ForeignKeyField(House, related_name='appointments')
    dt = DateTimeField()
