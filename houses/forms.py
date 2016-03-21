from flask_wtf import Form
from wtforms import (TextField,
                     IntegerField,
                     DateTimeField,
                     BooleanField,
                     PasswordField)
from wtforms.validators import (Required)


class LoginForm(Form):
    username = TextField('Username', [Required()])
    password = PasswordField('Password', [Required()])


class NewSellerForm(Form):
    name = TextField('Name')


class NewHouseForm(Form):


class NewCriterionForm(Form):


class NewAppointmentForm(Form):


class AvailabilityForm(Form):
    pass
