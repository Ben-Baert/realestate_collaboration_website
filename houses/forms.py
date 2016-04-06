import re
from string import (ascii_lowercase,
                    ascii_uppercase)
from flask.ext.login import current_user
from flask_wtf import Form as FlaskForm
from wtforms.fields import (TextField,
                            FieldList,
                            HiddenField,
                            IntegerField,
                            DateTimeField,
                            BooleanField,
                            SelectField,
                            FormField,
                            PasswordField)
from wtforms.validators import (Required,
                                Length,
                                Email,
                                Optional,
                                EqualTo,
                                URL)
from wtforms import ValidationError
from wtfpeewee.orm import (model_form,
                           ModelConverter)
from wtfpeewee.fields import ModelHiddenField
from .models import (User,
                     House,
                     Criterion,
                     Appointment,
                     UserAvailability,
                     Message)


class PasswordValidation:
    def __init__(self):
        pass

    def __call__(self, form, field):
        if len(field.data) < 8:
            raise ValidationError(
              """
              Password should be at least 8 characters long
              """)
        if not any(character in field.data for character in ascii_lowercase):
            raise ValidationError(
              """
              Password should contain at least one lowercase letter
              """)
        if not any(character in field.data for character in ascii_uppercase):
            raise ValidationError(
              """
              Password should contain at least one uppercase letter
              """)
        if not any(character in field.data for character in "0123456789"):
            raise ValidationError(
              """
              Password should contain at least one digit
              """)


def convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class BaseForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        prefix = convert(self.__class__.__name__.lower())
        FlaskForm.__init__(self, *args, prefix=prefix, **kwargs)

    def create_object(self, model, **kwargs):
        #  obj = model()
        attributes = {**dict(self.data.items()), **kwargs}
        #  print(attributes)
        #  for name, value in attributes.items():
        #      setattr(obj, name, value)
        obj = model.create(**attributes)
        return obj

    def edit_object(self, obj):
        for name, value in self.data.items():
            setattr(obj, name, value)
        obj.save()


class HouseForm(FlaskForm):
    url = TextField("URL", validators=[Required()])

    def validate_url(form, field):
        if not (field.data.startswith("http://www.realo.be/") or
                field.data.startswith("https://www.realo.be/")):
            raise ValidationError("URL must be a Realo url")

converter = ModelConverter(overrides={"password": PasswordField})


class HiddenHouseConverter(ModelConverter):
    def handle_foreign_key(self, model, field, **kwargs):
        return field.name, ModelHiddenField(model=field.rel_model, **kwargs)

house_hidden = HiddenHouseConverter()


def generate_form(model, base_class=BaseForm, converter=converter, **kwargs):
    return model_form(model,
                      base_class=base_class,
                      converter=converter, **kwargs)


LoginForm = generate_form(User, exclude=['email'])


class BaseSettingsForm(BaseForm):
    current_password = PasswordField("Current password (required!)",
                                     validators=[Required()])

    def validate_current_password(form, field):
        if not current_user.verify_password(field.data):
            raise ValidationError("Incorrect password")


SettingsForm = generate_form(User,
                             base_class=BaseSettingsForm,
                             field_args={
                                         "username": dict(validators=[Length(min=3)]),
    "password": dict(label="New password (optional)",
                     validators=[PasswordValidation(),
                                 Optional()]),
    "email": dict(validators=[Email()])
    })

CriterionForm = generate_form(Criterion)

MessageForm = generate_form(Message,
                            exclude=["author", "house", "dt"],
                            converter=house_hidden)

UserAvailabilityForm = generate_form(UserAvailability, exclude=["user"])
AppointmentForm = generate_form(Appointment, exclude=["house"])
