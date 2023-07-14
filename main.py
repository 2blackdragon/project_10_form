from flask import Flask, redirect, render_template, abort, request, url_for, flash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from flask_mail import Mail, Message

from users import User
from jobs import Job
from departments import Department
from tasks import Task

from forms import LoginForm, RegisterForm, EditAccForm, AddJob, EditJob, Search, AddDepartment, AddTask, EditTask

from data import db_session

from functools import wraps
from threading import Thread
from itsdangerous import URLSafeTimedSerializer


app = Flask(__name__)
# защита от CSRF-атаки (межсайтовая подделка запросов)
app.config['SECRET_KEY'] = 'B8P6Bm5seEU6425WclrF'

app.config['SECURITY_PASSWORD_SALT'] = 'si43u9kjDIUNFi4800bvkl90nlspd84IBL4nv9'
# настройки для отправления электронного письма
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'monitoring.proyectov@gmail.com'
app.config['MAIL_DEFAULT_SENDER'] = 'monitoring.proyectov@gmail.com'
app.config['MAIL_PASSWORD'] = 'mz6UDk3OCi'

mail = Mail(app)


# декоратор для проверки входа пользователя в систему
def check_login(func):
    @wraps(func)
    def decoration_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect('/login')
        return func(*args, **kwargs)
    return decoration_function


# декоратор, который проверяет подтверждение почты
def check_confirmed(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if current_user.confirmed is False:
            return redirect('/unconfirmed')
        return func(*args, **kwargs)
    return decorated_function


# функция для ассихронного отправления письма
def async_send_mail(app, msg):
    with app.app_context():
        mail.send(msg)


# отправление письма
def send_email(subject, recipient, template, **kwargs):
    msg = Message(subject, sender=app.config['MAIL_DEFAULT_SENDER'], recipients=[recipient])
    msg.html = render_template(template,  **kwargs)
    thr = Thread(target=async_send_mail,  args=[app,  msg])
    thr.start()
    return thr


# Создаем ссылку для пользователя
def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


# Вытаскиваем email из созданной нами ссылки
def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except:
        return False
    return email


login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/')
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


#опечаточка
@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    db_sess = db_session.create_session()
    form.department.choices = [depart.name for depart in db_sess.query(Department)]
    if form.validate_on_submit():
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пользователь с такой почтой уже существует")
        user = User()
        user.email = form.email.data
        user.password = user.hash_password(form.password.data)
        user.name = form.name.data
        user.surname = form.surname.data
        user.midname = form.midname.data
        user.name_lower = (form.surname.data + ' ' + form.name.data + ' ' + form.midname.data).lower()
        user.department = form.department.data
        user.phone = form.phone.data

        db_sess.add(user)
        db_sess.commit()

        token = generate_confirmation_token(user.email)
        confirm_url = url_for('confirm_email', token=token, _external=True)
        subject = 'Подтверждение аккаунта'
        send_email(subject, user.email, 'email_text.html', confirm_url=confirm_url)

        login_user(user)

        return redirect('/unconfirmed')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/confirm_email/<token>', methods=['GET', 'POST'])
def confirm_email(token):
    try:
        email = confirm_token(token)
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == email).first()
        if not user:
            abort(404)
        if not user.confirmed:
            if user.id == 1:
                user.admin = True
            user.confirmed = True
            db_sess.add(user)
            db_sess.commit()
        return redirect('/')
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')


@app.route('/unconfirmed')
@check_login
def unconfirmed():
    if current_user.confirmed:
        return redirect('/')
    return render_template('unconfirmed.html')


@app.route('/resend')
@check_login
def resend_confirmation():
    token = generate_confirmation_token(current_user.email)
    confirm_url = url_for('confirm_email', token=token, _external=True)
    subject = "Подтверждение аккаунта"
    send_email(subject, current_user.email, 'email_text.html', confirm_url=confirm_url)
    return redirect('/unconfirmed')


@app.route('/profile')
@check_login
@check_confirmed
def profile():
    return render_template('profile.html', title='Профиль', user=current_user)


@app.route('/edit_profile', methods=['GET', 'POST'])
@check_login
@check_confirmed
def edit_profile():
    form = EditAccForm()
    db_sess = db_session.create_session()
    form.department.choices = [depart.name for depart in db_sess.query(Department)]
    if request.method == "GET":
        form.email.data = current_user.email
        form.name.data = current_user.name
        form.surname.data = current_user.surname
        form.midname.data = current_user.midname
        form.department.data = current_user.department
        form.phone.data = current_user.phone
    if form.validate_on_submit():
        if [user for user in db_sess.query(User).all() if user.id != current_user.id and user.email == current_user.id]:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пользователь с такой почтой уже существует")
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        if user:
            change_email = False
            if user.email != form.email.data:
                change_email = True
            user.email = form.email.data
            user.password = current_user.hash_password(form.password.data)
            user.name = form.name.data
            user.surname = form.surname.data
            user.midname = form.midname.data
            user.name_lower = (form.surname.data + ' ' + form.name.data + ' ' + form.midname.data).lower()
            user.department = form.department.data
            user.phone = form.phone.data
            db_sess.commit()

            if change_email:
                token = generate_confirmation_token(user.email)
                confirm_url = url_for('confirm_email', token=token, _external=True)
                subject = 'Подтверждение аккаунта'
                send_email(subject, user.email, 'email_text.html', confirm_url=confirm_url)

                login_user(user)
                return redirect('/unconfirmed')
            return redirect('/profile')
        else:
            abort(404)
    return render_template('register.html', form=form, title='Редактирование профиля')


@app.route('/', methods=['GET', 'POST'])
@check_login
@check_confirmed
def main_page():
    form = Search()
    db_sess = db_session.create_session()
    if form.validate_on_submit():
        search_item = form.name.data
        if search_item:
            search_item = search_item.strip()
            if search_item:
                jobs = db_sess.query(Job).filter(Job.name_lower.like(f"%{search_item.lower()}%")).all()
                users = db_sess.query(User).all()
                names = {str(name.id): (name.surname, name.name) for name in users}
                descriptions = dict()
                collaborators = dict()
                collaborators_list = dict()
                team_leaders = dict()
                team_leaders_list = dict()
                for job in jobs:
                    descriptions[job.id] = job.description
                    collaborators[job.id] = []
                    collaborators_list[job.id] = []
                    team_leaders[job.id] = []
                    team_leaders_list[job.id] = []
                    for i in job.collaborators.split(', '):
                        collaborators[job.id].append(' '.join(names[str(i)]))
                        collaborators_list[job.id].append(int(i))
                    for i in job.team_leaders.split(', '):
                        team_leaders[job.id].append(' '.join(names[str(i)]))
                        team_leaders_list[job.id].append(int(i))
                return render_template('main_page.html', title='Главная страница', form=form, jobs=jobs, names=names,
                                       description=descriptions, collaborators=collaborators,
                                       collaborators_list=collaborators_list,
                                       team_leaders=team_leaders, team_leaders_list=team_leaders_list)
    jobs = db_sess.query(Job).all()
    users = db_sess.query(User).all()
    names = {str(name.id): (name.surname, name.name) for name in users}
    descriptions = dict()
    collaborators = dict()
    collaborators_list = dict()
    team_leaders = dict()
    team_leaders_list = dict()
    for job in jobs:
        descriptions[job.id] = job.description
        collaborators[job.id] = []
        collaborators_list[job.id] = []
        team_leaders[job.id] = []
        team_leaders_list[job.id] = []
        for i in job.collaborators.split(', '):
            collaborators[job.id].append(' '.join(names[str(i)]))
            collaborators_list[job.id].append(int(i))
        for i in job.team_leaders.split(', '):
            team_leaders[job.id].append(' '.join(names[str(i)]))
            team_leaders_list[job.id].append(int(i))
    return render_template('main_page.html', title='Главная страница', form=form, jobs=jobs, names=names,
                           description=descriptions, collaborators=collaborators, collaborators_list=collaborators_list,
                           team_leaders=team_leaders, team_leaders_list=team_leaders_list)


@app.route('/addjob', methods=['GET', 'POST'])
@check_login
@check_confirmed
def add_job():
    form = AddJob()
    if request.method == "GET":
        if form.validate_on_submit():
            return redirect('/')
        return render_template('add_job.html', title='Добавление работы', form=form)
    elif request.method == 'POST':
        try:
            db_sess = db_session.create_session()
            # Запомиаем все id сотрудников
            ids = [user.id for user in db_sess.query(User).all()]
            # Запоминаем имена всех проектов
            names = [job.name for job in db_sess.query(Job).all()]
            # Проверка формата ввода для поля тимлидов и наличия их id в бд
            for i in form.team_leaders.data.split(', '):
                if not i.isdigit():
                    return render_template('add_job.html', title='Авторизация',
                                           form=form, message='Ошибка в входных данных')
                if int(i) not in ids:
                    return render_template('add_job.html', title='Авторизация',
                                           form=form, message=f'Работника с номером {i} не существует')
            # Проверка формата ввода для поля работников и наличия их id в бд
            for i in form.collaborators.data.split(', '):
                if not i.isdigit():
                    return render_template('add_job.html', title='Авторизация',
                                           form=form, message='Ошибка в входных данных')
                if int(i) not in ids:
                    return render_template('add_job.html', title='Авторизация',
                                           form=form, message=f'Работника с номером {i} не существует')
            # Проверяем название проекта на уникальность
            if form.name.data in names:
                return render_template('add_job.html', title='Авторизация',
                                       form=form, message=f'Проект с таким названием уже существует')

            job = Job()
            job.name = form.name.data
            job.name_lower = form.name.data.lower()
            job.description = form.description.data
            job.team_leaders = form.team_leaders.data
            job.collaborators = form.collaborators.data
            job.is_finished = form.is_finished.data
            db_sess.add(job)
            db_sess.commit()
            return redirect('/')
        except:
            form = AddJob()
            return render_template('add_job.html', title='Авторизация',
                                   form=form, message='Ошибка в входных данных')


@app.route('/jobs/<int:id>', methods=['GET', 'POST'])
@check_login
@check_confirmed
def edit_job(id):
    form = EditJob()
    if request.method == "GET":
        db_sess = db_session.create_session()
        job = db_sess.query(Job).filter(Job.id == id).first()
        if job:
            if current_user.id not in list(map(int, job.team_leaders.split(', '))) \
                    and not current_user.admin:
                abort(403)
            form.name.data = job.name
            form.description.data = job.description
            form.team_leaders.data = job.team_leaders
            form.collaborators.data = job.collaborators
            form.is_finished.data = job.is_finished
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        job = db_sess.query(Job).filter(Job.id == id).first()
        if job:
            if current_user.id not in list(map(int, job.team_leaders.split(', '))) \
                    and not current_user.admin:
                abort(403)
            # Запомиаем все id сотрудников
            ids = [user.id for user in db_sess.query(User).all()]
            # Запоминаем имена всех проектов
            names = [job.name for job in db_sess.query(Job).all() if job.id != id]
            # Проверка формата ввода для поля тимлидов и наличия их id в бд
            for i in form.team_leaders.data.split(', '):
                if not i.isdigit():
                    return render_template('add_job.html', title='Авторизация',
                                           form=form, message='Ошибка в входных данных')
                if int(i) not in ids:
                    return render_template('add_job.html', title='Авторизация',
                                           form=form, message=f'Работника с номером {i} не существует')
            # Проверка формата ввода для поля работников и наличия их id в бд
            for i in form.collaborators.data.split(', '):
                if not i.isdigit():
                    return render_template('add_job.html', title='Авторизация',
                                           form=form, message='Ошибка в входных данных')
                if int(i) not in ids:
                    return render_template('add_job.html', title='Авторизация',
                                           form=form, message=f'Работника с номером {i} не существует')
            # Проверяем название проекта на уникальность
            if form.name.data in names:
                return render_template('add_job.html', title='Авторизация',
                                       form=form, message=f'Проект с таким названием уже существует')

            job.name = form.name.data
            job.name_lower = form.name.data.lower()
            job.description = form.description.data
            job.team_leaders = form.team_leaders.data
            job.collaborators = form.collaborators.data
            job.is_finished = form.is_finished.data
            db_sess.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('add_job.html', title='Редактирование проекта', form=form)


@app.route('/job_delete/<int:id>', methods=['GET', 'POST'])
@check_login
@check_confirmed
def delete_job(id):
    db_sess = db_session.create_session()
    job = db_sess.query(Job).filter(Job.id == id).first()
    tasks = db_sess.query(Task).filter(Task.job_id == id).all()
    if job:
        if current_user.id not in list(map(int, job.team_leaders.split(', '))) \
                and not current_user.admin:
            abort(403)
        db_sess.delete(job)
        for task in tasks:
            db_sess.delete(task)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/')


@app.route('/show_tasks/<int:id>', methods=['GET', 'POST'])
@check_login
@check_confirmed
def show_tasks(id):
    form = Search()
    db_sess = db_session.create_session()
    if form.validate_on_submit():
        search_item = form.name.data
        if search_item:
            search_item = search_item.strip()
            if search_item:
                tasks = db_sess.query(Task).filter(Task.name_lower.like(f'%{search_item.lower()}%')).all()
                job = db_sess.query(Job).filter(Job.id == id).first()
                team_leaders = list(map(int, job.team_leaders.split(', ')))
                collaborators = list(map(int, job.collaborators.split(', ')))
                return render_template("tasks.html", title='Задачи', form=form, job=job, tasks=tasks,
                                       team_leaders=team_leaders, collaborators=collaborators)
    tasks = db_sess.query(Task).filter(Task.job_id == id).all()
    job = db_sess.query(Job).filter(Job.id == id).first()
    team_leaders = list(map(int, job.team_leaders.split(', ')))
    collaborators = list(map(int, job.collaborators.split(', ')))
    return render_template("tasks.html", title='Задачи', form=form, job=job, tasks=tasks, team_leaders=team_leaders,
                           collaborators=collaborators)


@app.route('/addtask/<int:id>', methods=['GET', 'POST'])
@check_login
@check_confirmed
def add_task(id):
    form = AddTask()
    if request.method == "GET":
        if form.validate_on_submit():
            return redirect(f"/show_tasks/{id}")
        return render_template('add_task.html', title='Добавление задачи', form=form)
    elif request.method == 'POST':
        db_sess = db_session.create_session()
        tasks = [task.name for task in db_sess.query(Task).filter(Task.job_id == id).all()]
        if form.name.data in tasks:
            return render_template('add_task.html', title='Добавление задачи', form=form,
                                   message='Такая задача уже существует')
        task = Task()
        task.name = form.name.data
        task.name_lower = form.name.data.lower()
        task.job_id = id
        task.is_completed = form.is_completed.data

        db_sess.add(task)
        db_sess.commit()
        return redirect(f"/show_tasks/{id}")


@app.route('/edit_task/<int:id>', methods=['GET', 'POST'])
@check_login
@check_confirmed
def edit_task(id):
    form = EditTask()
    if request.method == "GET":
        db_sess = db_session.create_session()
        task = db_sess.query(Task).filter(Task.id == id).first()
        job = db_sess.query(Job).filter(Job.id == task.job_id).first()
        if task:
            if current_user.id not in list(map(int, job.team_leaders.split(', '))) \
                    and current_user.id not in list(map(int, job.collaborators.split(', '))) \
                    and not current_user.admin:
                abort(403)
            form.name.data = task.name
            form.is_completed.data = task.is_completed
        else:
            abort(404)
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        task_c = db_sess.query(Task).filter(Task.id == id).first()
        job = db_sess.query(Job).filter(Job.id == task_c.job_id).first()
        if task_c:
            if current_user.id not in list(map(int, job.team_leaders.split(', '))) \
                    and current_user.id not in list(map(int, job.collaborators.split(', '))) \
                    and not current_user.admin:
                abort(403)
            tasks = [task.name for task in db_sess.query(Task).filter(Task.job_id == task_c.job_id).all()]
            if form.name.data in tasks and form.name.data != task_c.name:
                return render_template('add_task.html', title='Изменение задачи', form=form,
                                       message='Такая задача уже существует')

            task_c.name = form.name.data
            task_c.name_lower = form.name.data.lower()
            task_c.is_completed = form.is_completed.data
            db_sess.commit()
            return redirect(f"/show_tasks/{job.id}")
        else:
            abort(404)
    return render_template('add_task.html', title='Редактирование задачи', form=form)


@app.route('/del_task/<int:id>', methods=['GET', 'POST'])
@check_login
@check_confirmed
def del_task(id):
    db_sess = db_session.create_session()
    task = db_sess.query(Task).filter(Task.id == id).first()
    job = db_sess.query(Job).filter(Job.id == task.job_id).first()
    if task:
        if current_user.id not in list(map(int, job.team_leaders.split(', '))) \
                and not current_user.admin:
            abort(403)
        db_sess.delete(task)
        db_sess.commit()
    else:
        abort(404)
    return redirect(f"/show_tasks/{job.id}")


@app.route('/show_users', methods=['GET', 'POST'])
@check_login
@check_confirmed
def show_users():
    form = Search()
    db_sess = db_session.create_session()
    if form.validate_on_submit():
        search_item = form.name.data
        if search_item:
            search_item = search_item.strip()
            if search_item:
                users = db_sess.query(User).filter(User.name_lower.like(f'%{search_item.lower()}%')).all()
                return render_template("users.html", title='Работники', form=form, users=users)
    users = db_sess.query(User).all()
    return render_template("users.html", title='Работники', form=form, users=users)


@app.route('/del_user/<int:id>')
@check_login
@check_confirmed
def del_user(id):
    if not current_user.admin:
        return abort(403)
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == id).first()
    if user:
        db_sess = db_session.create_session()
        db_sess.delete(user)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/show_users')


@app.route('/set_admin/<int:id>')
@check_login
@check_login
def set_admin(id):
    if not current_user.admin:
        return abort(403)
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == id).first()
    if user:
        user.admin = True
        db_sess.commit()
    else:
        abort(404)
    return redirect('/show_users')


@app.route('/departments', methods=['GET', 'POST'])
@check_login
@check_confirmed
def departments():
    if not current_user.admin:
        return abort(403)
    form = Search()
    db_sess = db_session.create_session()
    if form.validate_on_submit():
        search_item = form.name.data
        if search_item:
            search_item = search_item.strip()
            if search_item:
                departs = db_sess.query(Department).filter(Department.name_lower.like(f'%{search_item.lower()}%')).all()
                return render_template("departments.html", title='Отделы', form=form, departments=departs)
    departs = db_sess.query(Department).all()
    return render_template("departments.html", title='Отделы', form=form,  departments=departs)


@app.route('/add_department', methods=['GET', 'POST'])
@check_login
@check_confirmed
def add_department():
    if not current_user.admin:
        return abort(403)
    form = AddDepartment()
    if request.method == "GET":
        if form.validate_on_submit():
            return redirect('/departments')
        return render_template('add_department.html', title='Добавление отдела', form=form)
    elif request.method == 'POST':
        db_sess = db_session.create_session()
        departs = [depart.name for depart in db_sess.query(Department)]
        if form.name.data in departs:
            return render_template('add_department.html', title='Добавление отдела', form=form,
                                   message='Такой отдел уже существует')
        depart = Department()
        depart.name = form.name.data
        depart.name_lower = form.name.data.lower()

        db_sess.add(depart)
        db_sess.commit()
        return redirect('/departments')


@app.route('/del_department/<int:id>')
@check_login
@check_confirmed
def del_department(id):
    if not current_user.admin:
        return abort(403)
    db_sess = db_session.create_session()
    depart = db_sess.query(Department).filter(Department.id == id).first()
    if depart:
        users = [user for user in db_sess.query(User) if user.department == depart.name]
        for user in users:
            user.department = 'Отдел не выбран'
        db_sess.delete(depart)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/departments')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


if __name__ == '__main__':
    database_name = "db/table.sqlite"
    db_session.global_init(database_name)
    app.run()
