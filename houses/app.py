@app.route('/')
def home():
    if logged_in():
        return redirect(url_for('houses_list'))
    return redirect(url_for('login_page'))


@app.route('/login/', methods=['GET', 'POST'])
def login_page():
    if request.method == 'GET':
        return render_template('login.html')
    if request.method == 'POST':
        pass


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


