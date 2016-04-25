from realestate import app
from realestate.models import (BaseModel,
                               User,
                               Realestate,
                               RealestateCriterion,
                               RealestateCriterionScore,
                               RealestateInformationCategory,
                               UserNotAvailableError,
                               DoesNotExist)
from .criteria import criteria_list


@app.before_first_request
def setup_database():
    for cls in BaseModel.tables():
        #  cls.drop_table(fail_silently=True)
        cls.create_table(fail_silently=True)
    try:
        User.get_or_create(username="Ben", password="degeleis2jaaroud")
        User.get_or_create(username="Melissa", password="degeleis2jaaroud")
    except UserNotAvailableError:
        pass


@app.before_first_request
def setup_builtin_criteria():
    extra_criteria = [
    ('privacy', 'Privacy', False, 10, ['house', 'land'])]
    for short, name, dealbreaker, importance, applies_to in criteria_list:
        try:
            criterion = RealestateCriterion.get(short=short)
        except DoesNotExist:
            criterion = RealestateCriterion.create(
                             short=short,
                             name=name,
                             dealbreaker=dealbreaker,
                             importance=importance,
                             applies_to_house='house' in applies_to,
                             applies_to_land='land' in applies_to,
                             builtin=True)
        for realestate in Realestate.select():
            RealestateCriterionScore.get_or_create(realestate=realestate,
                                                   criterion=criterion)


@app.before_first_request
def setup_information():
    INFORMATION = [
        ("year", "Year", "Bouwjaar", ['house']),
        ("cadastral_income", "Cadastral income", "Kadastraal Inkomen", ['house']),
        ("spatial_planning", "Spatial planning", "Ruimtelijke ordening", ['house']),
        ("epc", "EPC score", "EPC waarde", ['house']),
        ("heating", "Heating", "Type verwarming", ['house']),
        ("building", "Building", "Bebouwing", ['house'])]
    for short, name, realo_name, applies_to in INFORMATION:
        RealestateInformationCategory.get_or_create(
                                       _short=short,
                                       _name=name,
                                       _realo_name=realo_name,
                                       applies_to_house='house' in applies_to,
                                       applies_to_land='land' in applies_to)
