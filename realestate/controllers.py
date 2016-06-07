import json
from functools import wraps
from flask import (redirect,
                   request,
                   url_for,
                   flash,
                   # g,
                   render_template,
                   abort,
                   jsonify)
from peewee import DoesNotExist, SelectQuery, IntegrityError
from flask.ext.login import (login_required,
                             login_user,
                             current_user,
                             logout_user,
                             current_app)
from realestate import app, csrf
from .forms import (LoginForm,
                    RealestateForm,
                    SettingsForm,
                    RealestateCriterionForm,
                    MessageForm,
                    AppointmentForm,
                    AppointmentsForm,
                    RealestateCriterionScoreForm,
                    RealestateInformationCategoryForm,
                    AdminUserForm,
                    RealestateInformationForm)
from .models import (User,
                     Realestate,
                     Notification,
                     RealestateCriterion,
                     Message,
                     Appointment,
                     RealestateInformation,
                     RealestateCriterionScore,
                     RealestateInformationCategory,
                     UserRealestateReview,
                     fn,
                     cache)
from .celery import add_realo_realestate, generate_feed, prepare_caches, add_from_json
from datetime import datetime


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
        if not current_user.is_authenticated or not current_user.is_admin:
            return abort(403)
        return func(*args, **kwargs)
    return decorated_view

def ownership_required(model):
    def outer(func):
        @wraps(func)
        def inner(*args, **kwargs):
            instance = model.get(model._id == kwargs['_id'])
            if not (current_user.is_admin or
                    instance.author == current_user):  # EDIT!
                return abort(403)
            return func(*args, **kwargs)
        return inner
    return outer


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
        return redirect(url_for('properties'))
    return redirect(url_for('login'))


@app.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        redirect(url_for('houses_list'))
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.get(username=form.username.data)
        except DoesNotExist:
            flash('User does not exist')
        else:
            if user.verify_password(form.password.data):
                if not user.is_active:
                    flash('Your account is not active')
                    return abort(403)
                login_user(user)
                flash('Successfully logged in as {}'.format(user.username))
                return redirect(url_for('notifications'))
            flash('The password you entered is incorrect')
    return render_template('login.html', form=form)

@app.route('/urls/')
def urls():
    return jsonify([r.realo_url for r in Realestate.select()])

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('You have successfully logged out')
    return(redirect(url_for('login')))


@app.route('/users/', methods=["GET", "POST"])
@admin_required
def users():
    users = User.select()

    return render_template("users.html", users=users)


@app.route('/user/<int:_id>/', methods=["GET", "POST"])
@admin_required
def user(_id):
    user = User.get(_id=_id)
    form = AdminUserForm(obj=user)
    if form.validate_on_submit():
        form.edit_object(user)
        return redirect(url_for('users'))

    return render_template("baseform.html", form=form)


@csrf.exempt
@app.route('/post_new_realestate/', methods=["POST"])
def post_new_realestate():
    new_realestate = request.get_json()
    auth = request.authorization
    if not (auth or auth.username == "cron" or auth.password == "hello"):
        abort(401)
    add_from_json.delay(new_realestate)
    for key, value in json.loads(new_realestate).items():
        print(value)
    return jsonify({"status_code": 200})

@app.route('/prepare_cache/')
def prepare_cache():
    prepare_caches.delay()
    return jsonify({"status_code": 200})

@app.route('/mark_as_sold/<int:_id>')
@login_required
def mark_as_sold(_id):
    re = Realestate.get(Realestate._id == _id)
    re.sold = True
    re.save()
    flash("The property in {} has been marked as sold!".format(re.address))
    return redirect(url_for('properties'))


@app.route('/generate_feed/<int:max_age>/')
@app.route('/generate_feed/', defaults={'max_age': 2})
@admin_required
def feed(max_age):
    generate_feed(max_age=max_age)
    return "Generating..."


@app.route('/information/', methods=["GET", "POST"])
@admin_required
def information():
    information = RealestateInformationCategory.select()

    return render_template("information.html",
                           information=information)


@app.route('/information/<int:_id>/', methods=["GET", "POST"])
@admin_required
def information_detail(_id):
    item = RealestateInformationCategory.get(_id=_id)
    form = RealestateInformationCategoryForm(obj=item)
    if form.validate_on_submit():
        form.edit_object(item)
        return redirect(url_for('information'))
    return render_template("baseform.html", form=form)


@app.route('/settings/', methods=["GET", "POST"])
@login_required
def settings():
    form = SettingsForm(obj=current_user)
    if form.validate_on_submit():
        form.edit_object(current_user)
        flash("Settings changed!")
        return redirect(url_for('houses'))
    return render_template('baseform.html', form=form)


@app.route('/prepare_queue/')
@admin_required
def prepare_queue():
    prepare_caches()
    return "preparing caches..."


@app.route('/queue/')
@login_required
def queue():
    try:
        realestate_id = current_user.cached_queue[0]
        to_go = len(current_user.cached_queue)
        realestate = Realestate.get(Realestate._id == realestate_id)
        if realestate.dealbreakers:
            flash('; '.join(dealbreaker.negative_description +
                            (" (" + dealbreaker.safecomment + ")"
                                if dealbreaker.safecomment else "")
                            for dealbreaker in realestate.dealbreakers),
                  "warning")
    except (IndexError, DoesNotExist):
        flash(
                """
                All properties have been reviewed.
                You have been redirected to the main properties page
                """,
                "info")
        return redirect(url_for('properties'))
    previous = request.args.get('previous', None)
    return render_template('queue.html',
                           realestate=realestate,
                           to_go=to_go,
                           previous=previous)


@app.route('/review/')
def review():
    _id, status = int(request.args.get('_id')), request.args.get('status')
    current_user.review_property(_id, status)
    return redirect(url_for('queue', previous=_id))


@app.route('/undo_review/<int:_id>/')
def undo_review(_id):
    current_user.undo_review(_id)
    return redirect(url_for('queue'))


@app.route("/properties/", methods=['GET', 'POST'], defaults={"categories": ['house', 'land']})
@app.route('/properties/<list:categories>/', methods=['GET', 'POST'])
@login_required
def properties(categories):
    page_nr = int(request.args.get('page') or 1)
    realestate = Realestate.not_rejected().where(Realestate.realestate_type << categories & ~Realestate.sold)
    total_nr_of_pages = realestate.count() // 12 + 1
    current_realestate = realestate#.paginate(page_nr, 12)
    previous_page = page_nr - 1 if page_nr > 1 else None
    next_page = page_nr + 1 if page_nr < total_nr_of_pages else None

    form = RealestateForm()
    if form.validate_on_submit():
        add_realo_realestate.delay(form.url.data)

        flash("Property created. It should be visible in a couple of minutes.", "info")

        return redirect(url_for('properties'))

    elif request.method == "POST":  # submitted but errors
        show_modal = True
    else:
        show_modal = False

    return render_template('houses_list.html',
                           realestate=current_realestate,
                           form=form,
                           show_modal=show_modal,
                           previous_page=previous_page,
                           next_page=next_page)


@app.route('/property/<int:_id>/', methods=["GET", "POST"])
@login_required
def realestate_detail(_id):
    realestate = get_object_or_404(Realestate, Realestate._id == _id)

    message_form = MessageForm()
    criterionscore_form = RealestateCriterionScoreForm(realestate=realestate)
    appointment_form = AppointmentForm()
    information_form = RealestateInformationForm(realestate=realestate)

    if information_form.validate_on_submit():
        for name, value in information_form.data.items():
            if not value:
                continue
            realestate_information_category = RealestateInformationCategory.get(
                (RealestateInformationCategory._short == name) |
                (fn.snakecase(RealestateInformationCategory._name) == name) |
                (fn.snakecase(RealestateInformationCategory._realo_name) == name))
            realestate_information, _ = RealestateInformation.get_or_create(category=realestate_information_category._id,
                                                                  realestate=realestate._id)
            realestate_information.value = value
            realestate_information.save()
        flash("Information updated")
        return redirect(url_for('realestate_detail', _id=_id))

    if message_form.validate_on_submit():
        message = message_form.create_object(Message, realestate=realestate._id)
        Notification.create('message', realestate, message._id)
        return redirect(url_for('realestate_detail', _id=_id))

    if criterionscore_form.validate_on_submit():
        for name, score in criterionscore_form.data.items():
            if score is "":
                continue
            criterion = RealestateCriterion.get(name=name)
            criterionscore = RealestateCriterionScore.get(
                criterion=criterion._id,
                realestate=realestate._id)
            try:
                criterionscore.score = int(score)
            except TypeError:
                pass  # Don't set, otherwise this overrules the defaultscore!!
            criterionscore.save()
        flash('Criteria updated')
        return redirect(url_for('realestate_detail', _id=_id))

    if appointment_form.validate_on_submit():
        appointment = appointment_form.create_object(
            Appointment, realestate=realestate._id)
        Notification.create('appointment', realestate, appointment._id)
        flash('Appointment made')
        return redirect(url_for('realestate_detail', _id=_id))

    if realestate.dealbreakers:
        flash("This house has serious issues: " +
              ', '.join(dealbreaker.negative_description + (" (" + dealbreaker.safecomment + ")" if dealbreaker.safecomment else "")
                        for dealbreaker in realestate.dealbreakers), "warning")
    return render_template('queue.html',
                           realestate=realestate,
                           criterionscore_form=criterionscore_form,
                           message_form=message_form,
                           appointment_form=appointment_form,
                           information_form=information_form)

@app.route('/notification/<int:_id>/')
def notification(_id):
    url_endpoints = {'realestate': 'realestate_detail',
                     'message': 'message',
                     'appointment': 'appointment'}
    notification_object = Notification.get(_id=_id)
    notification_object.read = True
    notification_object.save()
    return redirect(url_for('realestate_detail',
                            _id=notification_object.realestate._id,
                            _anchor=(notification_object.category +
                                     "-" +
                                     str(notification_object.object_id))))


@app.route('/criteria/', methods=["GET", "POST"])
@login_required
def criteria():
    criteria = RealestateCriterion.select()
    form = RealestateCriterionForm()
    if form.validate_on_submit():
        criterion = form.create_object(RealestateCriterion)
        for realestate in Realestate.select():
            RealestateCriterionScore.create(criterion=criterion, realestate=realestate)
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
    criterion = RealestateCriterion.get(_id=_id)
    form = RealestateCriterionForm(obj=criterion)
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
        realestate = Realestate.get(appointment.realestate)
        Notification.create('appointment', realestate._id, realestate.town)
        flash("Appointment made")

    return render_template('appointments.html',
                           appointments=appointments,
                           form=form)


@app.route("/notifications/")
@login_required
def notifications():
    notifications = (Notification
                     .select()
                     .where(Notification.user == current_user._id))

    return render_template('notifications.html',
                           notifications=notifications)


@app.route("/message/<int:_id>/", methods=["GET", "POST"])
@ownership_required(Message)
def message(_id):
    message = Message.get(Message._id == _id)
    #if not (message.author == current_user._id or current_user.is_admin):
    #    abort(403)
    message_form = MessageForm(obj=message)

    if message_form.validate_on_submit():
        message_form.edit_object(message)
        return redirect(url_for('realestate_detail', _id=message.realestate._id))

    return render_template("baseform.html",
                            form=message_form)
