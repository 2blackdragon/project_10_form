import sqlalchemy
from data.db_session import SqlAlchemyBase
from flask_login import UserMixin


class Task(SqlAlchemyBase, UserMixin):
    __tablename__ = 'tasks'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    job_id = sqlalchemy.Column(sqlalchemy.Integer)
    name = sqlalchemy.Column(sqlalchemy.String)
    name_lower = sqlalchemy.Column(sqlalchemy.String)
    is_completed = sqlalchemy.Column(sqlalchemy.Boolean)