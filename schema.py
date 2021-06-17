import marshmallow
import models
from main import ma
from flask_marshmallow import Marshmallow
from marshmallow_enum import EnumField


###################
# REQUEST SCHEMAS #
###################

class CourseRequestSchema(ma.Schema):
    name = marshmallow.fields.Str(required=True)
    price = marshmallow.fields.Int(required=True)


class UserRequestSchema(ma.Schema):
    email = marshmallow.fields.Email(required=True)
    password = marshmallow.fields.Str(required=True)
    name = marshmallow.fields.Str(required=True)
    surname = marshmallow.fields.Str(required=True)
    role = marshmallow.fields.Str(required=True)


class UserLoginRequestSchema(ma.Schema):
    email = marshmallow.fields.Str(required=True)
    password = marshmallow.fields.Str(required=True)


class RoleRequestSchema(ma.Schema):
    role = marshmallow.fields.Str()


class TeacherCourseRequestSchema(ma.Schema):
    course_id = marshmallow.fields.List(marshmallow.fields.Int)


class StudentCourseRequestSchema(ma.Schema):
    comment = marshmallow.fields.Str(allow_none=True)


class EditStudentCourseRequestSchema(StudentCourseRequestSchema):
    mark = marshmallow.fields.Int()


class EditStudentCourseRequestTeacherSchema(ma.Schema):
    complete = marshmallow.fields.Boolean()


####################
# RESPONSE SCHEMAS #
####################

class CourseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.Course


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.User

    role = EnumField(models.models.RoleEnum)


class UserLoginSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.User
        exclude = ['password']

    role = EnumField(models.models.RoleEnum)


class TeacherCourseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.User

    course = ma.Nested(CourseSchema, many=True)
    role = EnumField(models.models.RoleEnum)


class UserCourseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.StudentCourse

    course = ma.Nested(CourseSchema)
    role = EnumField(models.models.RoleEnum)