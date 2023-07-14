import sqlalchemy
from data.db_session import SqlAlchemyBase
from flask_login import UserMixin


class Department(SqlAlchemyBase, UserMixin):
    __tablename__ = 'departments'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, unique=True)
    name_lower = sqlalchemy.Column(sqlalchemy.String)
