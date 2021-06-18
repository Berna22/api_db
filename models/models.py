import enum

from core import db
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime, date
from dateutil import parser

import flask_restful
from sqlalchemy.exc import IntegrityError
from sqlalchemy import cast, Date


class NotSQLAlchemyObjectError(Exception):
    """

    """
    pass


def get_error(error_obj):
    """
    Method used for getting db IntegrityError, try to get duplicated key (ERR_DUPLICATED_EMAIL, ...) error or return
    general error ERR_DUPLICATED_ENTRY
    :param error_obj:
    :return:
    """
    try:
        str_error = str(error_obj.__dict__.get('orig')).split('\'')[-2].split('.')[1]
        return 'ERR_DUPLICATED_{}'.format(str_error.upper())
    except:
        return 'ERR_DUPLICATED_ENTRY'


def edit_sqlalchemy_object(obj, set_nulls=False, **kwargs):
    """

    :param obj:
    :param set_nulls:
    :param kwargs:
    :return:
    """
    if not hasattr(obj, '__table__'):
        raise NotSQLAlchemyObjectError('object myst have __table__ property')
    try:
        for arg in kwargs:
            if hasattr(obj, arg) and (set_nulls or kwargs.get(arg) is not None) and arg in obj.__table__.c:
                # need to think of better way to check for boolean values
                if kwargs.get(arg) in ['true', 'false', 'True', 'False']:
                    setattr(obj, arg, kwargs.get(arg) in ['true', 'True'])
                elif obj.__table__.c[arg].type.python_type in [datetime, date]:
                    if type(kwargs.get(arg)) == str:
                        setattr(obj, arg, parser.parse(kwargs.get(arg)))
                    elif type(kwargs.get(arg)) in [date, datetime]:
                        setattr(obj, arg, kwargs.get(arg))
                    elif set_nulls and kwargs.get(arg) is None:
                        setattr(obj, arg, kwargs.get(arg))
                    else:
                        # TODO raise error
                        pass
                elif type(kwargs.get(arg)) == list and type(obj.__table__.c[arg].type) == db.JSON:
                    setattr(obj, arg, kwargs.get(arg))
                else:
                    if kwargs.get(arg) is None:
                        if set_nulls:
                            setattr(obj, arg, None)
                    else:
                        setattr(obj, arg, obj.__table__.c[arg].type.python_type(kwargs.get(arg)))

        db.session.add(obj)

        # If object is creating add date
        if not obj.date_of_creation:
            obj.date_of_creation = datetime.today()

        # Update date_of_update field
        if hasattr(obj, 'date_of_update'):
            setattr(obj, 'date_of_update', datetime.today())

        db.session.commit()
    except IntegrityError as err:
        db.session.rollback()
        print('IntegrityError EDIT METHOD - ', err)
        flask_restful.abort(400, error=get_error(error_obj=err))


class BaseModel(object):
    """

    """

    # FIELDS #
    @declared_attr
    def id(self):
        return db.Column(db.Integer, primary_key=True, autoincrement=True)

    @declared_attr
    def date_of_creation(self):
        return db.deferred(db.Column(db.DateTime, nullable=False, server_default=db.func.now()))

    @declared_attr
    def date_of_update(self):
        return db.deferred(
            db.Column(db.DateTime, nullable=False, onupdate=db.func.now(), server_default=db.func.now()))

    @classmethod
    def create(cls, **kwargs):
        create_obj = cls()
        edit_sqlalchemy_object(create_obj, **kwargs)
        # create_obj.date_of_creation = datetime.utcnow()
        return create_obj

    # EDIT AND CREATE METHODS #
    def edit(self, set_nulls=False, **kwargs):
        if isinstance(self, db.Model):
            edit_sqlalchemy_object(self, set_nulls, **kwargs)

    @classmethod
    def get_all(cls):
        if hasattr(cls, "query"):
            return cls.query.order_by(cls.date_of_creation.desc()).all()

    @classmethod
    def _get_all_paginate(cls, cls_query, page, per_page):
        return cls_query.\
            order_by(cls.date_of_creation.desc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

    @classmethod
    def get_all_paginate(cls, page, per_page):
        if hasattr(cls, "query"):
            return cls._get_all_paginate(cls_query=cls.query, page=page, per_page=per_page).items


class RoleEnum(enum.Enum):
    teacher = 'teacher'
    student = 'student'


user_course_association = db.Table(
    'con_user_course', db.Model.metadata,
    db.Column('user_id', db.Integer, db.ForeignKey('tbl_user.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('tbl_course.id')))


class User(db.Model, BaseModel):
    __tablename__ = 'tbl_user'

    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.deferred(db.Column(db.Text))
    name = db.Column(db.String(120), nullable=False)
    surname = db.Column(db.String(120), nullable=False)
    role = db.Column(db.Enum(RoleEnum), nullable=False)

    course = db.relationship('Course', secondary=user_course_association, lazy='dynamic')

    @classmethod
    def get_by_id(cls, user_id):
        return cls.query.filter(cls.id == user_id).first()

    @classmethod
    def get_by_role(cls, user_id, role):
        return cls.query.filter(cls.role == role, cls.id == user_id).first()

    @classmethod
    def get_all_by_role(cls, role):
        return cls.query.filter(cls.role == role).all()

    @classmethod
    def get_by_email_and_password(cls, email, password):
        return cls.query.filter(cls.email == email, cls.password == password).first()

    @classmethod
    def get_course_for_teacher(cls, teacher_id):
        return cls.query\
            .join(user_course_association, cls.id == user_course_association.c.user_id)\
            .join(Course, user_course_association.c.course_id == Course.id)\
            .filter(cls.id == teacher_id).all()


class UserSession(db.Model, BaseModel):
    """
    Model for User session
    """
    __tablename__ = 'tbl_user_session'

    user_id = db.Column(db.Integer, db.ForeignKey('tbl_user.id'), nullable=False)
    session_id = db.Column(db.String(150), nullable=False)
    session_date = db.Column(db.Date, default=date.today())

    user = db.relationship('User')

    @classmethod
    def get_by_session_id(cls, session_id):
        return cls.query.filter(
            cls.session_id == session_id,
            db.cast(cls.date_of_creation, db.Date) == date.today(),
        ).first()


class Course(db.Model, BaseModel):
    __tablename__ = 'tbl_course'

    teacher_id = db.Column(db.Integer, db.ForeignKey('tbl_user.id'))
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    average_mark = db.Column(db.Integer, default=0)
    description = db.Column(db.Text)

    @classmethod
    def get_by_id(cls, course_id):
        return cls.query.filter(cls.id == course_id).first()


class StudentCourse(db.Model, BaseModel):
    __tablename__ = 'tbl_student_course'

    course_id = db.Column(db.Integer, db.ForeignKey('tbl_course.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('tbl_user.id'))
    complete = db.Column(db.Boolean, default=False, server_default=db.false())
    comment = db.Column(db.Text)
    mark = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True, server_default=db.true())

    course = db.relationship('Course')
    user = db.relationship('User')

    @classmethod
    def get_all_for_user(cls, student_id):
        return cls.query.filter(cls.student_id == student_id, ~cls.complete).all()

    @classmethod
    def get_course_for_user(cls, student_id, course_id):
        return cls.query.filter(cls.student_id == student_id, cls.course_id == course_id).first()

    @classmethod
    def get_course_for_teacher(cls, teacher_id, student_id, course_id):
        return cls.query.join(Course, cls.course_id == Course.id)\
            .filter(Course.teacher_id == teacher_id, cls.student_id == student_id, cls.course_id == course_id).first()

    @classmethod
    def student_filter(cls, course_id, start_date, complete):
        return cls.query\
            .filter(cast(cls.date_of_creation, Date) <= start_date, cls.course_id == course_id, cls.complete == complete)\
            .all()
