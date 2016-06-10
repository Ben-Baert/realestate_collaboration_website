import re
from string import (ascii_lowercase,
                    ascii_uppercase)
from peewee import DoesNotExist
from flask_login import current_user
from flask_wtf import Form as FlaskForm
from flask_pagedown.fields import PageDownField
from wtforms.compat import iteritems
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
                                URL,
                                NumberRange)
from wtforms import ValidationError
from wtforms.form import FormMeta
from wtfpeewee.orm import (model_form,
                           ModelConverter)
from wtfpeewee.fields import ModelHiddenField
from .models import (User,
                     Realestate,
                     RealestateCriterion,
                     Appointment,
                     UserAvailability,
                     Message,
                     RealestateCriterionScore,
                     RealestateInformation,
                     RealestateInformationCategory)
from .utils import (camel_to_snake,
                    snake_to_camel,
                    to_snakecase)


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


class BaseMeta(FormMeta):
    def __call__(cls, *args, **kwargs):
        cls._prefix = camel_to_snake(cls.__name__.lower())
        setattr(cls, "formname", HiddenField("formname", default=cls._prefix))
        return FormMeta.__call__(cls, *args, **kwargs)


class RealestateCriterionFormMeta(BaseMeta):
    def __call__(cls, realestate, *args, **kwargs):
        for criterion in realestate.criteria:
            if criterion.builtin:
                continue
            if ((realestate.realestate_type == 'house' and not criterion.applies_to_house) or
                (realestate.realestate_type == 'land' and not criterion.applies_to_land)):
                continue
            if not criterion.criterion.dealbreaker:
                field = IntegerField(criterion.criterion.name,
                             default=criterion.score,
                             description=criterion.criterion.formula,
                             validators=[Optional(), NumberRange(min=0, max=10)])
            else:
                field = BooleanField(criterion.criterion.name,
                                     default=True if criterion.score else False,
                                     description=criterion.criterion.formula,
                                     )
            setattr(cls, criterion.criterion.name, field)
        return BaseMeta.__call__(cls, *args, **kwargs)


class RealestateInformationFormMeta(BaseMeta):
    def __call__(cls, realestate, *args, **kwargs):
        for category in RealestateInformationCategory.select():
            if ((realestate.realestate_type == 'house' and not category.applies_to_house) or
                (realestate.realestate_type == 'land' and not category.applies_to_land)):
                continue
            realestate_information, _ = (RealestateInformation
                                         .get_or_create(category=category._id,
                                                        realestate=realestate._id))
            field = TextField(category.name,
                              default=realestate_information.value)
            setattr(cls, category.short, field)
        return BaseMeta.__call__(cls, *args, **kwargs)


class BaseForm(FlaskForm, metaclass=BaseMeta):
    def validate_on_submit(self):
        return (super().validate_on_submit() and
                self.formname.data == self.__class__._prefix)

    def create_object(self, model, **kwargs):
        attributes = {**dict(self.data.items()), **kwargs}
        obj = model.create(**attributes)
        return obj

    def edit_object(self, obj):
        for name, value in self.data.items():
            setattr(obj, name, value)
        obj.save()

    @property
    def data(self):
        d = super().data
        d.pop('formname')
        return d


class RealestateCriterionScoreForm(BaseForm, metaclass=RealestateCriterionFormMeta):
    pass


class RealestateInformationForm(BaseForm, metaclass=RealestateInformationFormMeta):
    pass


class RealestateForm(FlaskForm):
    url = TextField("URL", validators=[Required()])

    def validate_url(form, field):
        if not (field.data.startswith("http://www.realo.be/") or
                field.data.startswith("https://www.realo.be/")):
            raise ValidationError("URL must be a Realo url")
        if not (field.data.startswith("http://www.realo.be/nl/") or
                field.data.startswith("https://www.realo.be/nl/")):
            raise ValidationError("URL must be a Dutch Realo URL")

converter = ModelConverter(overrides={"password": PasswordField})


class HiddenHouseConverter(ModelConverter):
    def handle_foreign_key(self, model, field, **kwargs):
        return field.name, ModelHiddenField(model=field.rel_model, **kwargs)

house_hidden = HiddenHouseConverter()


def generate_form(model, base_class=BaseForm, converter=converter, **kwargs):
    return model_form(model,
                      base_class=base_class,
                      converter=converter, **kwargs)


LoginForm = generate_form(User, exclude=['email', 'active'])


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

class UnderScoreConverter(ModelConverter):
    def convert(self, model, field, field_args):
        if field.name.startswith("_"):
            field.name = field.name[1:]
        return super().convert(model, field, field_args)

underscore_converter = UnderScoreConverter()

RealestateCriterionForm = generate_form(RealestateCriterion, converter=underscore_converter)

converter = ModelConverter(overrides={"password": PageDownField})

class MessageForm(BaseForm):
    body = PageDownField()

UserAvailabilityForm = generate_form(UserAvailability, exclude=["user"])
AppointmentForm = generate_form(Appointment, exclude=["realestate"])
AppointmentsForm = generate_form(Appointment)




RealestateInformationCategoryForm = generate_form(RealestateInformationCategory,
                                             converter=underscore_converter)
AdminUserForm = generate_form(User, exclude=["password"])
