from flask import (redirect,
                   request,
                   url_for,
                   flash,
                   g,
                   render_template)
from peewee import DoesNotExist
from flask.ext.login import (login_required,
                             login_user,
                             current_user,
                             logout_user)
from .app import app
from .forms import (LoginForm,
                    SellerForm,
                    HouseForm,
                    SettingsForm,
                    CriterionForm,
                    MessageForm,
                    AppointmentForm)
from .models import (User,
                     House,
                     Seller,
                     Notification,
                     Criterion,
                     Picture,
                     Message,
                     Appointment)


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
                flash('Successfully logged in')
                return redirect(url_for('notifications'))
            flash('The password you entered is incorrect')
    return render_template('login.html', form=form)


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('You have successfully logged out')
    return(redirect(url_for('login')))


@app.route('/settings/', methods=["GET", "POST"])
@login_required
def settings():
    form = SettingsForm(obj=current_user)
    if form.validate_on_submit():
        form.edit_object(current_user)
        flash("Settings changed!")
        return redirect(url_for('houses'))
    return render_template('baseform.html', form=form)


@app.route('/houses/', methods=['GET', 'POST'])
@login_required
def houses():
    houses = House.select()

    form = HouseForm()
    if form.validate_on_submit():
        house = form.create_object(House)

        for picture in form.pictures.entries:
            Picture.create(
                house=house.id,
                description=picture.data['description'],
                url=picture.data['url'])

        flash("House created")

        for user in User.select().where(User.id != current_user.id):
            notification = Notification.create(user=user,
                                               house=house,
                                               category='house')
            notification.body = """
            <a href="/notification/{}/">New house in {}</a> added by {}
            """.format(str(notification.id), house.town, current_user.username)
            notification.save()

        return redirect(url_for('house_detail', id=house.id))

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
    house = House.get(House.id == _id)
    houses = House.select()

    message_form = MessageForm(house=house)
    if message_form.validate_on_submit():
        message_form.create_object(Message, house=_id, author=current_user.id)
        return redirect(url_for('houses', _id=_id))

    return render_template('house_detail.html',
                            house=house,
                            houses=houses,
                            message_form=message_form)


@app.route('/notification/<int:id>/')
def notification(id):
    url_endpoints = {'house': 'house_detail'}
    notification_object = Notification.get(Notification.id == id)
    notification_object.read = True
    notification_object.save()
    return redirect(url_for(url_endpoints[notification_object.category], id=notification_object.object_id))


@app.route('/sellers/', methods=['GET', 'POST'])
@login_required
def sellers():
    sellers = Seller.select()

    form = SellerForm()
    if form.validate_on_submit():
        form.create_object(Seller)
        flash("Seller created!")
        return redirect(url_for('sellers'))

    elif request.method == "POST":
        show_modal = True
    else:
        show_modal = False

    return render_template('sellers.html',
                           sellers=sellers,
                           form=form,
                           show_modal=show_modal)


@app.route('/seller/<int:id>/', methods=['GET', 'POST'])
@login_required
def seller(id):
    try:
        seller = Seller.get(id=id)
    except DoesNotExist:
        flash("Seller with id: {} does not exist!".format(id))
        return redirect(url_for('sellers'))

    form = SellerForm(obj=seller)
    if form.validate_on_submit():
        form.edit_object(seller)
        flash("Seller updated!")
        return redirect(url_for('sellers'))

    elif request.method == "POST":
        show_modal = True
    else:
        show_modal = False

    return render_template('baseform.html',
                           title="Edit {}".format(seller.name),
                           form=form,
                           show_modal=show_modal)


@app.route('/delete_seller/<int:id>/')
@login_required
def delete_seller(id):
    try:
        seller = Seller.get(id=id)
    except DoesNotExist:
        flash("Seller with id: {} does not exist!".format(id))
        return redirect(url_for('sellers'))

    seller.delete_instance()
    flash('Seller deleted')
    return redirect(url_for('sellers'))


@app.route('/criteria/', methods=["GET", "POST"])
@login_required
def criteria():
    criteria = Criterion.select()
    form = CriterionForm()
    if form.validate_on_submit():
        form.create_object(Criterion)
        flash("Criterion created")
    elif request.method == "POST":
        show_modal = True
    else:
        show_modal = False

    return render_template('criteria.html',
                            criteria=criteria,
                            form=form,
                            show_modal=show_modal)


@app.route('/appointments/')
@login_required
def appointments():
    appointments = Appointment.select().order_by(Appointment.dt)
    form = AppointmentForm()
    if form.validate_on_submit():
        form.create_object(Appointment)
        for user in User.others():
            Notification.create(user=user,
                                )

    return render_template('appointments.html',
                            appointments=appointments)




@app.route("/notifications/")
@login_required
def notifications():
    notifications = Notification.select().where(Notification.user == current_user.id)

    return render_template('notifications.html',
                           notifications=notifications)
