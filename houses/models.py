from datetime import datetime
from flask.ext.login import UserMixin, current_user
from geopy.distance import vincenty
from peewee import (SqliteDatabase,
                    Model,
                    CharField,
                    IntegrityError,
                    BooleanField,
                    IntegerField,
                    TextField,
                    FloatField,
                    ForeignKeyField,
                    DateTimeField,
                    PrimaryKeyField)
from .app import bcrypt, celery
from .utils import to_snakecase
import houses.criteria



database = SqliteDatabase('houses.db')


class UserNotAvailableError(Exception):
    pass


class BaseModel(Model):
    _id = PrimaryKeyField(primary_key=True)  # avoid shadowing built-in id
                                             # and/or unnecessary ambiguity
    def readable_date(self):
        return self.dt.strftime("%d/%m/%Y")

    def readable_time(self):
        return self.dt.strftime("%H:%M")

    def readable_datetime(self):
        return self.dt.strftime("%d/%m/%Y %H:%M")

    @classmethod
    def tables(cls):
        children = []

        for subclass in cls.__subclasses__():
            children.append(subclass)
            children.extend(subclass.tables())

        return children

    class Meta:
        database = database

    def __repr__(self):
        return self._id


class User(BaseModel, UserMixin):
    username = CharField(unique=True,
                         max_length=30)
    password = CharField()
    email = CharField(null=True)
    active = BooleanField(default=True)

    def __repr__(self):
        return self.username

    @classmethod
    def create(cls, **kwargs):
        hashed_password = bcrypt.generate_password_hash(kwargs.pop('password'))

        user = cls(password=hashed_password, **kwargs)

        try:
            user.save()
        except IntegrityError:
            raise UserNotAvailableError(
                """
                The user you attempted to create already exists
                """)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password)
        self.save()

    def verify_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def others(self):
        return User.select().where(User._id != self._id)

    @property
    def is_admin(self):
        return self.username == "Ben"

    @property
    def is_active(self):
        return self.active


class Criterion(BaseModel):
    short = CharField()
    name = CharField(max_length=30)
    dealbreaker = BooleanField(default=False)
    importance = IntegerField(default=0, null=True)
    formula = TextField(null=True)
    explanation = TextField(null=True)

    @property
    def clean_name(self):
        return to_snakecase(self.name)

    @property
    def builtin(self):
        return hasattr(self.clean_name, 'criteria')

    def delete_instance(self, *args, **kwargs):
        if self.builtin:
            raise NotImplementedError(
            '''
            You can't just remove a builtin criterion.
            ''')

    def __repr__(self):
        return self.name

    class Meta:
        order_by = ('-dealbreaker', '-importance')

#class LatLngField(Field):
#    pass


class Land(BaseModel):
    pass


class House(BaseModel):
    class Meta:
        order_by = ('-sold',)

    added_at = DateTimeField(default=datetime.now())
    added_by = ForeignKeyField(User, related_name='houses_added')

    seller = CharField()
    price = IntegerField()
    # land_only = BooleanField(default=False)
    sold = BooleanField(default=False)

    address = CharField()
    lat = FloatField(null=True)
    lng = FloatField(null=True)

    realo_url = CharField(null=True, unique=True)
    immoweb_url = CharField(null=True, unique=True)
    description = CharField(null=True)

    visited = BooleanField(default=False)

    _thumbnail_pictures = TextField()
    _main_pictures = TextField()

    def __repr__(self):
        return self.town

    def distance_to(self, lat, lng):
        return vincenty((self.lat, self.lng), (lat, lng))

    def nearby_houses(self):
        pass

    def appointment_proposals(self):
        pass

    @classmethod
    def next_appointment(self):
        pass

    @property
    def town(self):
        return self.address.split()[-1]

    @property
    def thumbnail_pictures(self):
        return self._thumbnail_pictures.split(",")

    @thumbnail_pictures.setter
    def thumbnail_pictures(self, value):
        self._thumbnail_pictures = ",".join(value)

    @thumbnail_pictures.deleter
    def thumbnail_pictures(self):
        self._thumbnail_pictures = None

    @property
    def main_pictures(self):
        return self._main_pictures.split(",")

    @main_pictures.setter
    def main_pictures(self, value):
        self._main_pictures = ",".join(value)

    @main_pictures.deleter
    def main_pictures(self):
        self._main_pictures = None

    @property
    def dealbreakers(self):
        return any(criterion.score == 0 and criterion.criterion.dealbreaker
                   for criterion in self.criteria)

    @property
    def score(self):
        """
        Calculates the score based on the items that have been filled in
        for this particular house. Obviously, the more items filled in,
        the more accurate the result will be.

        This is not very efficient, but will be refactored
        (or so I hope, at least) later if necessary.
        """
        if self.dealbreakers:
            return 0
        max_score = sum(10 * criterion.criterion.importance
                        for criterion in self.criteria
                        if not criterion.criterion.dealbreaker)
        actual_score = sum((criterion.score or 0) *
                           criterion.criterion.importance
                           for criterion in self.criteria
                           if not criterion.criterion.dealbreaker)
        try:
            return round(actual_score / max_score * 100)
        except (ZeroDivisionError, TypeError):
            return 0

    def __getattr__(self, short):
        #try:
        category = HouseInformationCategory.get(HouseInformationCategory.short == short)
        return HouseInformation.get(HouseInformation.house == self._id,
                                        HouseInformation.category == category).value
        #except AttributeError:
        #    raise NotImplementedError("Something went wrong! {}".format(short)) #return None


class HouseInformationCategory(BaseModel):
    short = CharField(unique=True, null=True)
    name = CharField(unique=True, null=True)
    realo_name = CharField(unique=True)

    def __repr__(self):
        return "{}: {}".format(self.__class__.__name__, self.name)


class HouseInformation(BaseModel):
    house = ForeignKeyField(House, related_name='information')
    category = ForeignKeyField(HouseInformationCategory)
    value = CharField()

    @property
    def name(self):
        return self.category.name or self.category.realo_name

    def __repr__(self):
        return "{} information for house in {}: {}".format(self.category.name,
                                                           self.house.town,
                                                           self.value)


class CriterionScore(BaseModel):
    """
    Set metaclass to detect if builtin.
    If so, set default value for score to the return
    value of the builtin function.
    """
    criterion = ForeignKeyField(Criterion, related_name='houses')
    house = ForeignKeyField(House, related_name='criteria')
    score = IntegerField(null=True)
    # , default=self.defaultscore)  # range 0-10, if dealbreaker range 0-1
    comment = TextField(null=True)

    @property
    def name(self):
        return self.criterion.name

    @property
    def short(self):
        return self.criterion.short

    @property
    def safescore(self):
        return self.score or self.defaultscore()

    @property
    def dealbreaker_failed(self):
        return self.criterion.dealbreaker and self.safescore == 0

    @property
    def dealbreaker_passed(self):
        return self.criterion.dealbreaker and self.safescore

    @property
    def score_unknown(self):
        return self.safescore is None

    def defaultscore(self):
        print("in defaultscore")
        #try:
        return getattr(houses.criteria, self.short)(self.house)
        #except AttributeError:
        #    print("fuck!")
        #    return None
        #except TypeError:
        #    raise NotImplementedError(
        #        """
        #       Excepted a function!
        #        """)

    def __repr__(self):
        return "{} score for house in {}: {}".format(self.criterion.name,
                                                     self.house.town,
                                                     self.score)


class Appointment(BaseModel):
    house = ForeignKeyField(House, related_name='appointments')
    dt = DateTimeField()

    class Meta:
        order_by = ('dt',)

    def __repr__(self):
        return "Appointment for house in {} at {}".format(self.house.town, self.readable_datetime())


class CustomBase(BaseModel):
    dt = DateTimeField(default=datetime.now())
    body = TextField()


class Message(CustomBase):
    author = ForeignKeyField(User, related_name='messages')
    house = ForeignKeyField(House, related_name='messages')

    @classmethod
    def create(cls, *args, **kwargs):
        obj = super(Message, cls).create(author=current_user._id, **kwargs)
        return obj

    def __repr__(self):
        return "{} by {} to house in {} posted at {}: {}".format(self.__class__.__name,
                                                                 self.author.username,
                                                                 self.house.town,
                                                                 self.body,
                                                                 self.readable_datetime())

    class Meta:
        order_by = ('dt',)


class Notification(CustomBase):
    user = ForeignKeyField(User)
    read = BooleanField(default=False)
    house = ForeignKeyField(House, null=True)
    category = CharField(choices=[('appointment', 'New appointment'),
                                  ('house', 'New house'),
                                  ('message', 'New message')])
    object_id = IntegerField()

    MESSAGES = {
        "house": "New house in {town} added by {username}",
        "appointment": "New appointment for house in {town} made by {username}",
        "message": "New message to house in {town} written by {username}"
    }

    @classmethod
    def create(cls, category, house, object_id=None):
        for user in current_user.others():
            print("User: " + user.username)
            obj = cls()
            obj.user = user._id
            obj.house = house._id
            obj.category = category
            obj.object_id = object_id or house._id
            try:
                message_string = cls.MESSAGES[category]
            except KeyError:
                raise ValueError(
                    """
                    Invalid category; valid categories are {}.
                    The one you entered is {}.
                    """.format(", ".join(cls.MESSAGES.keys()), category))
            obj.body = message_string.format(
                    **{"town": house.town,
                     "username": current_user.username})
            obj.save()
            obj.body = (
                """
                <a href="/notification/{}/">{}</a>
                """).format(str(obj._id),
                            obj.body)
            obj.save()

    class Meta:
        order_by = ('-dt',)


class UserAvailability(BaseModel):
    """
    Book appointments only when all users are available
    """
    user = ForeignKeyField(User, related_name='available')
    dt = DateTimeField()

    class Meta:
        order_by = ('dt',)
