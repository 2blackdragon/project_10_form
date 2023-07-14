from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, SelectField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    email = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegisterForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль',
                             validators=[DataRequired(),
                                         Length(min=10, message='Минимальная длина '
                                                                'пароля 10 символов')])
    name = StringField('Имя', validators=[DataRequired()])
    surname = StringField('Фамилия', validators=[DataRequired()])
    midname = StringField('Отчество', validators=[DataRequired()])
    department = SelectField('Отдел')
    phone = StringField('Телефон', validators=[DataRequired()])
    submit = SubmitField('Регистрация')


class EditAccForm(FlaskForm):
    email = EmailField('Почта', validators=[DataRequired()])
    password = PasswordField('Пароль',
                             validators=[DataRequired(),
                                         Length(min=10, message='Минимальная длина '
                                                                'пароля 10 символов')])
    name = StringField('Имя', validators=[DataRequired()])
    surname = StringField('Фамилия', validators=[DataRequired()])
    midname = StringField('Отчество', validators=[DataRequired()])
    department = SelectField('Отдел')
    phone = StringField('Телефон', validators=[DataRequired()])
    submit = SubmitField('Редактировать')


class AddJob(FlaskForm):
    name = StringField('Название проекта', validators=[DataRequired()])
    description = StringField('Описание проекта', validators=[DataRequired()])
    team_leaders = StringField('Номера кураторов проекта через запятую', validators=[DataRequired()])
    collaborators = StringField('Номера работников над проектом через запятую', validators=[DataRequired()])
    is_finished = BooleanField('Завершён')
    submit = SubmitField('Добавить')


class EditJob(FlaskForm):
    name = StringField('Название проекта', validators=[DataRequired()])
    description = StringField('Описание проекта', validators=[DataRequired()])
    team_leaders = StringField('Номера кураторов проекта через запятую', validators=[DataRequired()])
    collaborators = StringField('Номера работников над проектом через запятую', validators=[DataRequired()])
    is_finished = BooleanField('Завершён')
    submit = SubmitField('Изменить')


class Search(FlaskForm):
    name = StringField()
    submit = SubmitField('Найти')


class AddDepartment(FlaskForm):
    name = StringField('Название отдела', validators=[DataRequired()])
    submit = SubmitField('Добавить')


class AddTask(FlaskForm):
    name = StringField('Задача', validators=[DataRequired()])
    is_completed = BooleanField('Завершена')
    submit = SubmitField('Добавить')


class EditTask(FlaskForm):
    name = StringField('Задача', validators=[DataRequired()])
    is_completed = BooleanField('Завершена')
    submit = SubmitField('Изменить')
