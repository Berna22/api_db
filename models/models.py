import enum

from core import db
from sqlalchemy.ext.declarative import declared_attr


class BaseModel(object):
    """

    """

    # FIELDS #
    @declared_attr
    def id(self):
        return db.Column(db.Integer, primary_key=True, autoincrement=True)


class User(db.Model, BaseModel):
    __tablename__ = 'tbl_user'

    name = db.Column(db.String(300))

    @classmethod
    def get_next_fifty(cls, offset):
        return cls.query.filter(cls.id >= offset).order_by(cls.id.asc()).limit(50)
