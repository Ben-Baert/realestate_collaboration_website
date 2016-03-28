from string import ascii_lowercase, ascii_uppercase
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
from wtforms.validators import (Required, Length, Email, Optional, EqualTo, URL)
from wtforms import ValidationError
from wtfpeewee.orm import model_form, ModelConverter
from wtfpeewee.fields import ModelHiddenField
from .models import Seller, User, House, Criterion, Appointment, UserAvailability, Picture, Message


class PasswordValidation:
    def __init__(self):
        pass

    def __call__(self, form, field):
        if len(field) < 8:
            raise ValidationError("Password should be at least 8 characters long")
        if not any(character in field for character in ascii_lowercase):
            raise ValidationError("Password should contain at least one lowercase letter")
        if not any(character in field for character in ascii_uppercase):
            raise ValidationError("Password should contain at least one uppercase letter")
        if not any(character in field for character in "0123456789"):
            raise ValidationError("Password should contain at least one digit")


class BaseForm(FlaskForm):
    def create_object(self, model, **kwargs):
        obj = model()
        attributes = {**dict(self.data.items()), **kwargs}
        for name, value in attributes.items():
            setattr(obj, name, value)
        obj.save()
        return obj

    def edit_object(self, obj):
        for name, value in self.data.items():
            setattr(obj, name, value)
        obj.save()


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


SettingsForm = generate_form(User, base_class=BaseSettingsForm, field_args={
    "username": dict(validators=[Length(min=3)]),
    "password": dict(label="New password (optional)",
                     validators=[Length(min=6), PasswordValidation(), Optional()]),
    "email": dict(validators=[Email()])
    })

SellerForm = generate_form(Seller)
CriterionForm = generate_form(Criterion)
PictureForm = generate_form(Picture, exclude=["house"],
                                     field_args={
                                     "url": dict(validators=[Required(), URL()])
                                     })

MessageForm = generate_form(Message, exclude=["author", "house", "dt"], converter=house_hidden)


class BaseHouseForm(BaseForm):
    pictures = FieldList(FormField(PictureForm), min_entries=1)

HouseForm = generate_form(House, exclude=["sold",
                                          "contacted",
                                          "visited",
                                          "street",
                                          "house_nr",
                                          "postal_code",
                                          "lat",
                                          "lng",
                                          "immo_url",
                                          "realo_url",
                                          "immoweb_url",
                                          "kapaza_url"],
                                base_class=BaseHouseForm,
                                 field_args={
                                 "main_url": dict(label="Link to house", validators=[Required(), URL()])
                                 })




UserAvailabilityForm = generate_form(UserAvailability, exclude=["user"])
AppointmentForm = generate_form(Appointment)
