from app import app
from .forms import LoginForm
from flask import (redirect,
                   url_for,
                   flash,
                   render_template)

@app.route('/')
def home():
    if logged_in():
        return redirect(url_for('houses_list'))
    return redirect(url_for('login'))


@app.route('/login/', methods=['GET', 'POST'])
def login_page():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('houses_list'))
    
    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.get(username=form.username.data).verify_password(form.password.data)
        except peewee.DoesNotExist:
            flash('User does not exist')
        else:
            if user.verify_password(form.password.data):
                login_user(user)
                flash('Successfully logged in')
                return redirect(url_for('houses_list'))
            else:
                flash('The password you entered is incorrect')
    return render_template('login', form=form)


@app.route('/houses/')
@login_required
def houses_list():
    houses = House.select()
    return render_template('houses_list.html',
                            houses=houses)


@app.route('/house/<id:int>/')
@login_required
def detail(id):
    house = House.get(id=id)
    interest_rate=0.410

    return render_template('detail.html', 
                            house=house)


@app.route('/new_house/', methods=['GET', 'POST'])
@login_required
def new_house():
    if request.method == 'GET':
        return render_template('new_house.html')
    if request.method == 'POST':
        pass


@app.route('/criteria/')
@login_required
def criteria_list():
    criteria = Criterion.select()

    return render_template('criteria_list.html',
                            criteria=criteria)


@app.route('/new_criterion/', methods=['GET', 'POST'])
@login_required
def new_criterion():
    if request.method == 'GET':
        return render_template('new_criterion.html')
    if request.method == 'POST':
        pass


@app.route('/appointments/')
@login_required
def appointment_list():
    appointments = Appointment.select().order_by(Appointment.dt)

    return render_template('appointment_list.hmtl',
                            appointments=appointments)


@app.route('/new_appointment/', methods=['GET', 'POST'])
@login_required
def new_appointment():
    if request.method == 'GET':
        return render_template('new_appointment.html')
    if request.method == 'POST':
        pass


