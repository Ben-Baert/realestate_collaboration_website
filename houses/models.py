from datetime import datetime
from flask.ext.login import UserMixin, current_user
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
from .app import bcrypt


database = SqliteDatabase('houses.db')


class UserNotAvailableError(Exception):
    pass


class BaseModel(Model):
    _id = PrimaryKeyField(primary_key=True)  # avoid shadowing built-in id
                                             # and/or unnecessary ambiguity

    def readable_date(self):
        return self.dt.format("%d/%m/%Y")

    def readable_time(self):
        return self.dt.format("%H:%M")

    @classmethod
    def tables(cls):
        children = []

        for subclass in cls.__subclasses__():
            children.append(subclass)
            children.extend(subclass.tables())

        return children

    class Meta:
        database = database


class User(BaseModel, UserMixin):
    username = CharField(unique=True,
                         max_length=30)
    password = CharField()
    email = CharField(null=True)

    @classmethod
    def create(cls, **kwargs):
        hashed_password = bcrypt.generate_password_hash(kwargs["password"])
        del kwargs["password"]

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

    @staticmethod
    def others():
        return User.select().where(User._id != current_user._id)


class Criterion(BaseModel):
    name = CharField(max_length=30)
    dealbreaker = BooleanField(default=False,
                               help_text=("""
        If True, any house with a score == 0 will be rejected.
        """))
    importance = IntegerField(default=5)
    formula = TextField()
    explanation = TextField(null=True)

    class Meta:
        order_by = ('-dealbreaker', '-importance')


class Seller(BaseModel):
    name = CharField(max_length=30)
    website = CharField(null=True)
    telephone_number = CharField(null=True)
    real_estate_agent = BooleanField(null=True)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


class House(BaseModel):
    class Meta:
        order_by = ('-sold',)

    seller = ForeignKeyField(Seller, related_name='houses')
    price = IntegerField()
    land_only = BooleanField(default=False)
    sold = BooleanField(default=False)

    street = CharField(null=True)
    house_nr = CharField(null=True)
    postal_code = CharField(null=True)
    town = CharField()
    lat = FloatField(null=True)
    lng = FloatField(null=True)

    immo_url = CharField(null=True)
    realo_url = CharField(null=True)
    immoweb_url = CharField(null=True)
    kapaza_url = CharField(null=True)

    contacted = BooleanField(default=False)
    visited = BooleanField(default=False)

    def address(self):
        return ' '.join(item
                        for item in [self.street, self.house_nr, self.town]
                        if item)

    def score(self):
        """
        Calculates the score based on the items that have been filled in
        for this particular house. Obviously, the more items filled in,
        the more accurate the result will be.

        This is not very efficient, but will be refactored
        (or so I hope, at least) later if necessary.
        """
        criteria = (CriterionScore.select(
                    CriterionScore.score, CriterionScore.importance)
                    .where(CriterionScore.house == self._id))
        max_score = sum(10 * criterion.importance for criterion in criteria)
        actual_score = sum(criterion.score * criterion.importance
                           for criterion in criteria)
        return actual_score / max_score


class Picture(BaseModel):
    house = ForeignKeyField(House, related_name='pictures')
    url = CharField()
    description = CharField(null=True)


class CriterionScore(BaseModel):
    criterion = ForeignKeyField(Criterion, related_name='houses')
    house = ForeignKeyField(House, related_name='criterion_scores')
    score = IntegerField()  # range 0-10
    comment = TextField()


class Appointment(BaseModel):
    house = ForeignKeyField(House, related_name='appointments')
    dt = DateTimeField()

    class Meta:
        order_by = ('dt',)


class CustomBase(BaseModel):
    user = ForeignKeyField(User)
    house = ForeignKeyField(House)
    dt = DateTimeField(default=datetime.now())
    read = BooleanField(default=False)
    body = TextField(null=True)

    @classmethod
    def create(cls, **kwargs):
        obj = cls()
        obj.user = current_user
        for name, value in kwargs.items():
            setattr(obj, name, value)
        obj.save()
        return obj

    class Meta:
        order_by = ('read', '-dt')


class Message(CustomBase):
    pass


class Notification(CustomBase):
    category = CharField(choices=[('appointment', 'New appointment'),
                                  ('house', 'New house'),
                                  ('message', 'New message')])


class UserAvailability(BaseModel):
    """
    Book appointments only when all users are available
    """
    user = ForeignKeyField(User, related_name='available')
    dt = DateTimeField()
