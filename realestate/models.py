import os
from datetime import datetime
from functools import total_ordering
from flask.ext.login import UserMixin, current_user
from geopy.distance import vincenty
from playhouse.sqlite_ext import SqliteExtDatabase
from playhouse.signals import Model, post_init, post_save
from peewee import (CharField,
                    IntegrityError,
                    BooleanField,
                    IntegerField,
                    TextField,
                    FloatField,
                    ForeignKeyField,
                    DateTimeField,
                    DateField,
                    PrimaryKeyField,
                    fn,
                    DoesNotExist)
from playhouse.hybrid import hybrid_method
from playhouse.hybrid import hybrid_property
from realestate import bcrypt
from .utils import to_snakecase
import realestate.criteria_funcs
from walrus import Database
from redis import Redis
import re
from config import REDIS_PORT, REDIS_PASSWORD, REALESTATE_ROOT

"""
Note on terminology:
    Realestate is used in Python classes and objects
    to represent any house or piece of land.
    In strings, the term 'property' is used.
"""

r = Redis(port=REDIS_PORT, password=REDIS_PASSWORD)

database = SqliteExtDatabase(os.path.join(REALESTATE_ROOT, 'houses.db'))

cache = Database(port=REDIS_PORT, password=REDIS_PASSWORD)


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

    @classmethod
    def get(cls, *args, **kwargs):
        """
        Hackish way to deal with properties while
        maintaining compatibility with Peewee
        """
        if args:
            return super().get(*args, **kwargs)
        defaults = kwargs.pop('defaults', {})
        query = cls.select()
        for field, value in kwargs.items():
            if '__' in field:
                query = query.filter(**{field: value})
            else:
                query = query.where(getattr(cls, field) == value)
        return query.get()


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

    @hybrid_property
    def is_admin(self):
        return self.username == "Ben"

    @hybrid_property
    def is_active(self):
        return self.active

    @property
    def cached_queue(self):
        return cache.List("realestate:" + str(self._id) + ":queue")

    def review_property(self, realestate_id, status):
        review, _ = UserRealestateReview.get_or_create(user=self._id,
                                                       realestate=realestate_id)
        review.status = status
        review.save()
        r.lrem("realestate:" + str(self._id) + ":queue", realestate_id, num=1)

    def undo_review(self, realestate_id):
        review = UserRealestateReview.get(UserRealestateReview.realestate == realestate_id &
                                          UserRealestateReview.user == self._id)
        review.delete_instance()
        self.cached_queue.prepend(realestate_id)


class RealestateCriterion(BaseModel):
    short = CharField()
    name = CharField(max_length=30, null=True)

    dealbreaker = BooleanField(default=False)
    importance = IntegerField(default=0, null=True)

    formula = TextField(null=True)
    explanation = TextField(null=True)

    _positive_description = TextField(null=True)
    _negative_description = TextField(null=True)
    _unknown_description = TextField(null=True)

    applies_to_house = BooleanField(null=True)
    applies_to_land = BooleanField(null=True)

    builtin = BooleanField(default=False)

    @hybrid_property
    def clean_name(self):
        return to_snakecase(self.name)

    def delete_instance(self, *args, **kwargs):
        if self.builtin:
            raise NotImplementedError(
                """
                You can't just remove a builtin criterion.
                """)
        return super().delete_instance(*args, **kwargs)

    @hybrid_property
    def positive_description(self):
        return self._positive_description or self.name

    @positive_description.setter
    def positive_description(self, value):
        self._positive_description = value

    @hybrid_property
    def negative_description(self):
        return self._negative_description or self.name

    @negative_description.setter
    def negative_description(self, value):
        self._negative_description = value

    @hybrid_property
    def unknown_description(self):
        return self._unknown_description or self.name

    @unknown_description.setter
    def unknown_description(self, value):
        self._unknown_description = value

    def __repr__(self):
        return self.name

    class Meta:
        order_by = ('-dealbreaker', '-importance')


@total_ordering
class Status:
    def __init__(self, int_value, string_value):
        self.int_value = int_value
        self.string_value = string_value

    def __str__(self):
        return self.string_value

    def __lt__(self, other):
        return self.int_value < other.int_value

    def __eq__(self, other):
        return self.int_value == other.int_value

ACCEPTED = Status(4, "Accepted")
CONTROVERSIAL = Status(3, "Controversial")
PENDING = Status(2, "Pending")
REJECTED = Status(1, "Rejected")


@database.func()
def rank_status(s):
    print(s)
    r = {"accepted": 4,
         "controversial": 3,
         "pending": 2,
         "rejected": 1}
    return r[s]


class Realestate(BaseModel):
    realestate_type = CharField(choices=[('land', 'Land'),
                                       ('house', 'House')])
    added_on = DateField(null=True)

    seller = CharField()
    price = IntegerField()
    sold = BooleanField(default=False)

    inhabitable_area = IntegerField(null=True)  # null for land
    total_area = IntegerField()

    address = CharField()
    lat = FloatField(null=True)
    lng = FloatField(null=True)

    realo_url = CharField(null=True, unique=True)
    description = CharField(null=True)

    visited = BooleanField(default=False)

    _thumbnail_pictures = TextField()
    _main_pictures = TextField()


    def __repr__(self):
        return self.address

    @hybrid_property
    def has_full_address(self):
        return bool(re.match(r'[\w\s\']+\s\d{1,4},\s\d{4}[\w\s\']+', self.address))

    @hybrid_method
    def distance_to(self, lat, lng):
        return vincenty((self.lat, self.lng), (lat, lng))

    @hybrid_property
    def nearby_properties(self):
        pass

    @hybrid_property
    def appointment_proposals(self):
        pass

    @classmethod
    def all(cls):
        return cls.select()

    @classmethod
    def not_rejected(cls):
        return (cls.select()
                   .join(UserRealestateReview)
                   .join(User)
                   .where(UserRealestateReview.status != 'rejected')
                   .group_by(cls._id)
                   .having(fn.COUNT(User._id) > 0))

    @classmethod
    def not_rejected_by_current_user(cls):
        return (cls.select().join(UserRealestateReview)
                            .where((UserRealestateReview.status != 'rejected') &
                                   (UserRealestateReview.user == current_user._id)))
                            #.order_by(fn.rank_status(cls.status), cls.score))

    @classmethod
    def houses_only(cls):
        return cls.select().where(cls.land_only == False)

    @classmethod
    def land_only(cls):
        return cls.select().where(cls.land_only == True)

    @classmethod
    def full_queue(cls, user):
        return cls.unreviewed_by(user)

    @classmethod
    def next_queue_item(cls, user):
        return cls.full_queue(user).get()

    @property
    def status(self):
        if self.reviews.count() < User.select().count():
            return "pending"
        if all(review.status == 'accepted' for review in self.reviews):
            return "accepted"
        if all(review.status == 'rejected' for review in self.reviews):
            return "rejected"
        return "controversial"

    @property
    def scorestatus(self):
        return rank_status(self.status) ** 10 + self.score

    @property
    def status_details(self):
        return '\n'.join(review.user.username + ": " + review.status for review in self.reviews)

    @classmethod
    def reviewed(cls, user):
        return cls.select().join(UserRealestateReview).where(UserRealestateReview.user == user._id)

    @classmethod
    def unreviewed_by(cls, user):
        return cls.select().where(~(cls._id << cls.reviewed(user)) & ~cls.sold)

    @hybrid_method
    def accepted_by(self, user):
        return (UserRealestateReview.get(realestate=self._id,
                                         user=user._id)
                is not None)

    @classmethod
    def accepted_properties(cls):
        return (cls.select()
                   .join(UserRealestateReview)
                   .where(UserRealestateReview.status == 'approved')
                   .having(fn.COUNT(UserRealestateReview._id) == 2)) #  HARDCODED USER COUNT

    @hybrid_property
    def rejected(self):
        return (UserRealestateReview.select()
                                    .where(realestate=self._id, status='rejected')
                                    .count() ==
                User.select().count())

    @hybrid_property
    def contested(self):
        return (UserRealestateReview.get(realestate=self._id, status='accepted') is not None and
                UserRealestateReview.get(realestate=self._id, status='rejected') is not None)

    @hybrid_method
    def checked(self, user):
        return user._id in self.reviewers

    @hybrid_method
    def unchecked(self, user):
        user_review = UserRealestateReview.get(UserRealestateReview.user == user._id,
                                               UserRealestateReview.realestate == self._id)
        return user_review is None

    @property
    def user_status(self):
        try:
            return UserRealestateReview.get(UserRealestateReview.user == current_user._id,
                                            UserRealestateReview.realestate == self._id).status
        except DoesNotExist:
            return None

    @hybrid_property
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

    @hybrid_property
    def has_dealbreakers(self):
        if self.dealbreakers:
            return True
        return False

    @property
    def criteria(self):
        if self.realestate_type == 'house':
            return (criterion for criterion in self._criteria if criterion.applies_to_house)
        return (criterion for criterion in self._criteria if criterion.applies_to_land)

    @property
    def dealbreakers(self):
        return [criterion
                for criterion in self.criteria
                if criterion.safescore == 0 and
                criterion.dealbreaker]

    @property
    def aspects(self):
        return (criterion
                for criterion in self.criteria
                if not criterion.dealbreaker and
                criterion.safescore is not None)

    @property
    def positive_aspects(self):
        return (aspect
                for aspect in self.aspects
                if aspect.safescore > 5)

    @property
    def negative_aspects(self):
        return (aspect
                for aspect in self.aspects
                if aspect.safescore <= 5)

    @property
    def actual_problems(self):
        return (criterion
                for criterion in self.criteria
                if criterion.dealbreaker and
                criterion.safescore == 0)

    @property
    def potential_problems(self):
        return (criterion
                for criterion in self.criteria
                if #criterion.dealbreaker and
                criterion.safescore is None)

    @property
    def information(self):
        if self.realestate_type == 'house':
            return (info for info in self._information if info.category.applies_to_house)
        return (info for info in self._information if info.category.applies_to_land)
    

    @hybrid_property
    def _score(self):
        """
        Calculates the score based on the items that have been filled in
        for this particular house. Obviously, the more items filled in,
        the more accurate the result will be.

        This is not very efficient, but will be refactored
        (or so I hope, at least) later if necessary.
        """
        max_score = sum(10 * criterion.importance
                        for criterion in self.criteria
                        if criterion.safescore is not None and
                        not criterion.dealbreaker)
        actual_score = sum(criterion.safescore * criterion.importance
                           for criterion in self.criteria
                           if criterion.safescore and
                           not criterion.dealbreaker)
        try:
            return round((actual_score / max_score) * 100)
        except (ZeroDivisionError, TypeError):
            return 0

    @hybrid_property
    def score(self):
        if self.has_dealbreakers:
            return 0
        return self._score


    def __getattr__(self, short):
        """
        This method makes it very easy to get information
        about a house. Instead of house.information.epc, one
        can simply do house.epc.
        """
        try:
            category = RealestateInformationCategory.get(RealestateInformationCategory._short == short)
            return RealestateInformation.get(RealestateInformation.realestate == self._id,
                                             RealestateInformation.category == category).value
        except (DoesNotExist, AttributeError):
            return None


class UserRealestateReview(BaseModel):
    user = ForeignKeyField(User, related_name='reviewed_realestate')
    realestate = ForeignKeyField(Realestate, related_name='reviews')
    dt = DateTimeField(default=datetime.now())
    status = CharField(choices=[('rejected', 'Rejected'),
                                ('unsure', 'Unsure'),
                                ('accepted', 'Accepted')], null=True)

    #class Meta:
    #    primary_key = CompositeKey('user', 'realestate')


@database.func()
def snakecase(val):
    return to_snakecase(val)


class Feature(BaseModel):
    name = CharField(max_length=15)


class RealestateFeature(BaseModel):
    realestate = ForeignKeyField(Realestate, related_name='features')
    feature = ForeignKeyField(Feature, related_name='realestate')


class RealestateInformationCategory(BaseModel):
    _short = CharField(unique=True, null=True)
    _name = CharField(unique=True, null=True)
    _realo_name = CharField(unique=True)

    applies_to_house = BooleanField(null=True)
    applies_to_land = BooleanField(null=True)
    #  dependent_criteria = TextField()

    @property
    def short(self):
        return (self._short or
                to_snakecase(self.name))

    @short.setter
    def short(self, value):
        self._short = value

    @property
    def name(self):
        return self._name or self._realo_name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def realo_name(self):
        return self._realo_name or self._name

    @realo_name.setter
    def realo_name(self, value):
        self._realo_name = value

    def __repr__(self):
        return "{}: {}".format(self.__class__.__name__, self.name)


class RealestateInformation(BaseModel):
    realestate = ForeignKeyField(Realestate, related_name='_information')
    category = ForeignKeyField(RealestateInformationCategory)
    value = CharField(null=True)

    @hybrid_property
    def name(self):
        return self.category.name

    def __repr__(self):
        return "{} information for property in {}: {}".format(self.category.name,
                                                           self.realestate.town,
                                                           self.value)


def after_save(sender, instance, created):
    """
    This refreshes all automated criteria for house when
    any information about house x is changed. Not very
    efficient, but this will do for now.
    The alternative is to keep a register of dependencies,
    and only refresh those dependencies when information is
    renewed.
    Given that information is rarely changed, I don't think
    it's worthwhile to implement this at this point.
    """
    to_be_updated = (RealestateCriterionScore
                     .select()
                     .where(RealestateCriterionScore.realestate == instance.realestate))
    for item in to_be_updated:
        item.get_defaults()

post_save.connect(after_save, sender=RealestateInformation)


class RealestateCriterionScore(BaseModel):
    criterion = ForeignKeyField(RealestateCriterion, related_name='realestate')
    realestate = ForeignKeyField(Realestate, related_name='_criteria')
    score = IntegerField(null=True)
    comment = TextField(null=True)
    defaultscore = IntegerField(null=True)
    defaultcomment = TextField(null=True)

    def __getattr__(self, name):
        return getattr(self.criterion, name, None)

    @property
    def safescore(self):
        if self.score is not None:  # making sure we catch 0/False
            return self.score
        return self.defaultscore

    @property
    def safecomment(self):
        return self.comment or self.defaultcomment or self.safescore

    @property
    def dealbreaker_failed(self):
        return self.criterion.dealbreaker and self.safescore == 0

    @property
    def dealbreaker_passed(self):
        return self.criterion.dealbreaker and self.safescore

    @property
    def score_unknown(self):
        return self.safescore is None

    def prepared(self):
        super().prepared()
        self.set_defaults()

    def set_defaults(self):
        if ((self.score is not None or self.defaultscore is not None) and
            (self.comment or self.defaultcomment)):
            return
        try:
            self.get_defaults()
        except TypeError as e:
            raise TypeError(e, self.short, self.realestate)

    def get_defaults(self):
        if not self.builtin:
            return
        try:
            self.defaultscore, self.defaultcomment = getattr(realestate.criteria_funcs, self.short)(self.realestate)
            self.save()
        except AttributeError as e:
            return None

    def __repr__(self):
        return "{} score for property in {}: {}".format(self.criterion.name,
                                                        self.realestate.town,
                                                        self.score)


class Appointment(BaseModel):
    realestate = ForeignKeyField(Realestate, related_name='appointments')
    dt = DateTimeField()

    class Meta:
        order_by = ('dt',)

    def __repr__(self):
        return ("Appointment for property in {} at {}"
                .format(self.realestate.town, self.readable_datetime()))


class CustomBase(BaseModel):
    dt = DateTimeField(default=datetime.now())
    body = TextField()


class Message(CustomBase):
    author = ForeignKeyField(User, related_name='messages')
    realestate = ForeignKeyField(Realestate, related_name='messages')

    @classmethod
    def create(cls, *args, **kwargs):
        obj = super(Message, cls).create(author=current_user._id, **kwargs)
        return obj

    def __repr__(self):
        return ("{} by {} to property in {} posted at {}: {}"
                .format(self.__class__.__name__,
                        self.author.username,
                        self.realestate.town,
                        self.body,
                        self.readable_datetime()))

    class Meta:
        order_by = ('dt',)


class Notification(CustomBase):
    user = ForeignKeyField(User)
    read = BooleanField(default=False)
    realestate = ForeignKeyField(Realestate, null=True)
    category = CharField(choices=[('appointment', 'New appointment'),
                                  ('house', 'New house'),
                                  ('land', 'New piece of land'),
                                  ('message', 'New message')])
    object_id = IntegerField()

    MESSAGES = {
        "house": "New house in {town} added by {username}",
        "land": "New piece of land in {town} added by {username}",
        "appointment": "New appointment for property in {town} made by {username}",
        "message": "New message to property in {town} written by {username}"
    }

    @classmethod
    def create(cls, category, realestate, object_id=None):
        for user in current_user.others():
            print("User: " + user.username)
            obj = cls()
            obj.user = user._id
            obj.realestate = realestate._id
            obj.category = category
            obj.object_id = object_id or realestate._id
            try:
                message_string = cls.MESSAGES[category]
            except KeyError:
                raise ValueError(
                    """
                    Invalid category; valid categories are {}.
                    The one you entered is {}.
                    """.format(", ".join(cls.MESSAGES.keys()), category))
            obj.body = message_string.format(
                    **{"town": realestate.town,
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
