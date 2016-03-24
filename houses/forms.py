from flask_wtf import Form
from wtforms.fields import (TextField,
                            HiddenField,
                            IntegerField,
                            DateTimeField,
                            BooleanField,
                            Selectfield,
                            FormField,
                            PasswordField)
from wtforms.validators import (Required)


class BaseForm(Form):
    pass

class LocationBaseForm(BaseForm):
    street = TextField('Street')
    house_nr = TextField('House number')
    town = TextField('Town', [Required()])


class LoginForm(BaseForm):
    username = TextField('Username', [Required()])
    password = PasswordField('Password', [Required()])


class NewSellerForm(BaseForm):
    name = TextField('Name', [Required()])
    website = TextField('Website', [Required()])
    phone_number = TextField('Phone number', [Required()])
    real_estate_agent = BooleanField('Real estate agent')


class NewHouseForm(BaseForm):
    seller = SelectField('Seller', [Required()]) 
    price = IntegerField('Price', [Required()])
    land_only = BooleanField('Land only')
    location = BaseFormField(LocationBaseForm)

    pictures = FieldList(TextField('Picture url'))

    year = IntegerField('Year')
    total_area = IntegerField('Total area')
    living_area = IntegerField('Living area')
    garden_area = IntegerField('Garden area')
    garage_area = IntegerField('Garage area')

    epc = IntegerField('EPC-score')
    heating = SelectField()

    time_to_leuven_in_minutes = IntegerField('Time to Leuven (minutes)')
    time_to_brussels_in_minutes = IntegerField('Time to Brussels (minutes)')
    distance_to_train_station = IntegerField('Distance to train station')
    proximity_to_forest = IntegerField('Distance to nearest forested area (meters)')


class NewCriterionBaseForm(BaseForm):
    name = TextField('Name', [Required()])
    importance = IntegerField('Importance', [Required()])
    instructions = TextField('Instructions', [Required()])

    #form_code = TextAreaField()
    #calculation_code = TextAreaField()

class NewAppointmentBaseForm(BaseForm):
    house = HiddenField()
    dt = DateTimeField()

class AvailabilityBaseForm(BaseForm):
    pass
