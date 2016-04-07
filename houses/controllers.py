from functools import wraps
from flask import (redirect,
                   request,
                   url_for,
                   flash,
                   g,
                   render_template,
                   abort)
from peewee import DoesNotExist, SelectQuery
from flask.ext.login import (login_required,
                             login_user,
                             current_user,
                             logout_user,
                             current_app)
from wtforms.fields import IntegerField
from .app import (app,
                  celery)
from .forms import (LoginForm,
                    HouseForm,
                    SettingsForm,
                    CriterionForm,
                    MessageForm,
                    AppointmentForm,
                    AppointmentsForm,
                    CriterionScoreForm)
from .models import (User,
                     House,
                     Notification,
                     Criterion,
                     Message,
                     Appointment,
                     HouseInformation,
                     CriterionScore)
from .scrapers import Realo

def get_object_or_404(query_or_model, *query):
    if not isinstance(query_or_model, SelectQuery):
        query_or_model = query_or_model.select()
    try:
        return query_or_model.where(*query).get()
    except DoesNotExist:
        abort(404)


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_admin:
            return abort(403)
        return func(*args, **kwargs)
    return decorated_view


def ownership_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_admin or current_user.is_owner:  # EDIT!
            return abort(403)
        return func(*args, **kwargs)
    return decorated_view


ERROR_MESSAGES = {
    401: "You are unauthenticated",
    403: "You are not authorised to access this page",
    404: "The page you requested was not found"
}


def base_error_handler(e):
    try:
        message = ERROR_MESSAGES[e.code]
    except KeyError:
        message = "Something went wrong"
    flash("{}. You have been redirected to the home page.".format(message))
    return redirect(url_for('home') or '/')

for key in ERROR_MESSAGES.keys():
    app.register_error_handler(key, base_error_handler)


@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('houses'))
    return redirect(url_for('login'))


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        redirect(url_for('houses_list'))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            print(form.username.data)
            user = User.get(username=form.username.data)
        except DoesNotExist:
            flash('User does not exist')
        else:
            if user.verify_password(form.password.data):
                login_user(user)
                flash('Successfully logged in as {}'.format(user.username))
                return redirect(url_for('notifications'))
            flash('The password you entered is incorrect')
    return render_template('login.html', form=form)


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('You have successfully logged out')
    return(redirect(url_for('login')))


@app.route('/users/', methods=["GET", "POST"])
@admin_required
def users():
    return "You're in!"


@app.route('/settings/', methods=["GET", "POST"])
@login_required
def settings():
    form = SettingsForm(obj=current_user)
    if form.validate_on_submit():
        form.edit_object(current_user)
        flash("Settings changed!")
        return redirect(url_for('houses'))
    return render_template('baseform.html', form=form)


@celery.task
def add_realo_house(url):
    print("started")
    with app.app_context():
        with Realo(url) as realo_house:
            lat, lng = realo_house.lat_lng()
            house = House.create(
                        added_by=current_user._id,
                        seller=realo_house.seller(),
                        address=realo_house.address(),
                        lat=lat,
                        lng=lng,
                        description=realo_house.description(),
                        price=realo_house.price(),
                        realo_url=url,
                        thumbnail_pictures=realo_house.thumbnail_pictures(),
                        main_pictures=realo_house.main_pictures(),
                        )

            for information in realo_house.information():
                HouseInformation.create(
                    house=house,
                    name=information[0],
                    value=information[1])

            for criterion in Criterion.select():
                CriterionScore.create(criterion=criterion, house=house)

            Notification.create('house', house)


@app.route('/houses/', methods=['GET', 'POST'])
@login_required
def houses():
    houses = House.select()#.order_by(House.score)

    form = HouseForm()
    if form.validate_on_submit():
        add_realo_house.delay(form.url.data)

        flash("House created. It should be visible in a couple of minutes.")

        return redirect(url_for('houses'))

    elif request.method == "POST":  # submitted but errors
        show_modal = True
    else:
        show_modal = False

    return render_template('houses_list.html',
                           houses=houses,
                           form=form,
                           show_modal=show_modal)


@app.route('/houses/<int:_id>/', methods=["GET", "POST"])
@login_required
def house_detail(_id):
    house = get_object_or_404(House, House._id == _id)
    houses = House.select()

    message_form = MessageForm()
    criterionscore_form = CriterionScoreForm(house=house)
    appointment_form = AppointmentForm()

    if message_form.validate_on_submit():
        message = message_form.create_object(Message, house=house._id)
        Notification.create('message', house, message._id)
        return redirect(url_for('house_detail', _id=_id))

    if criterionscore_form.validate_on_submit():
        for name, score in criterionscore_form.data.items():
            criterion = Criterion.get(Criterion.name == name)
            criterionscore = CriterionScore.get(
                CriterionScore.criterion == criterion._id,
                CriterionScore.house == house._id)
            criterionscore.score = int(score)
            criterionscore.save()
        flash('Criteria updated')
        return redirect(url_for('house_detail', _id=_id))

    if appointment_form.validate_on_submit():
        appointment = appointment_form.create_object(
            Appointment, house=house._id)
        Notification.create('appointment', house, appointment._id)
        flash('Appointment made')
        return redirect(url_for('house_detail', _id=_id))

    return render_template('house_detail.html',
                           house=house,
                           houses=houses,
                           criterionscore_form=criterionscore_form,
                           message_form=message_form,
                           appointment_form=appointment_form)


@app.route('/notification/<int:_id>/')
def notification(_id):
    url_endpoints = {'house': 'house_detail',
                     'message': 'message',
                     'appointment': 'appointment'}
    notification_object = Notification.get(Notification._id == _id)
    notification_object.read = True
    notification_object.save()
    return redirect(url_for('house_detail',
                            _id=notification_object.house._id,
                            _anchor=notification_object.category + "-" + str(notification_object.object_id)))


@app.route('/criteria/', methods=["GET", "POST"])
@login_required
def criteria():
    criteria = Criterion.select()
    form = CriterionForm()
    if form.validate_on_submit():
        criterion = form.create_object(Criterion)
        for house in House.select():
            CriterionScore.create(criterion=criterion, house=house)
        flash("Criterion created")
        return redirect(url_for('criteria'))
    elif request.method == "POST":
        show_modal = True
    else:
        show_modal = False

    return render_template('criteria.html',
                           criteria=criteria,
                           form=form,
                           show_modal=show_modal)


@app.route('/criterion/<int:_id>/', methods=["GET", "POST"])
def criterion(_id):
    criterion = Criterion.get(Criterion._id == _id)
    form = CriterionForm(obj=criterion)
    if form.validate_on_submit():
        form.edit_object(criterion)
        flash('Criterion updated')
        return redirect(url_for('criteria'))

    return render_template("baseform.html",
                           form=form)


@app.route('/appointments/', methods=["GET", "POST"])
@login_required
def appointments():
    appointments = Appointment.select().order_by(Appointment.dt)

    form = AppointmentsForm()
    if form.validate_on_submit():
        appointment = form.create_object(Appointment)
        house = House.get(appointment.house)
        Notification.create('appointment', house._id, house.town)
        flash("Appointment made")

    return render_template('appointments.html',
                           appointments=appointments,
                           form=form,
                           )

@app.route("/notifications/")
@login_required
def notifications():
    notifications = (Notification
                     .select()
                     .where(Notification.user == current_user._id))

    return render_template('notifications.html',
                           notifications=notifications)
