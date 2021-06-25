import threading

import flask
from flask import request, Blueprint, jsonify, make_response

import errors
import models
import schema
from datetime import datetime, date
import time
from utils import decorators

api_calls = Blueprint('api_calls', __name__)


def generate_and_update_user_session_key(user):
    import hashlib

    user_session_key = hashlib.sha512("{}/{}".format(user.id, datetime.utcnow()).encode("UTF-8")).hexdigest()

    session_key = "{}:{}:{}".format("sess", user.id, user_session_key)

    return session_key


@api_calls.route('/courses/<int:course_id>', methods=['GET', 'PATCH', 'DELETE'])
@api_calls.route('/courses', methods=['GET', 'POST'])
@decorators.check_session_role(models.RoleEnum.teacher, return_user=True)
def course_teacher_api(current_user, course_id=None):
    """ Get a course or all courses"""
    if request.method == 'GET':

        if course_id:
            return schema.CourseSchema(many=False).dump(models.Course.get_by_id(course_id))

        return schema.CourseSchema(many=True).dumps(models.Course.get_all(), indent=4)

    if request.method == 'POST':
        """ Create a course"""

        validated_data = schema.CourseRequestSchema().load(flask.request.json or {})

        validated_data['teacher_id'] = current_user.id

        # Create course
        course = models.Course.create(**validated_data)

        # Add new course to teacher course connection table
        if course not in current_user.course:
            current_user.course.append(course)

        return schema.CourseSchema(many=False).dump(course)

    if request.method == 'PATCH':
        """ Edit Course"""

        validated_data = schema.CourseRequestSchema().load(flask.request.json or {})

        course = models.Course.get_by_id(course_id=course_id)

        if not course:
            flask.abort(make_response(jsonify(errors=errors.ERR_BAD_COURSE_ID), 400))

        # If logged in teacher didn't create the course, throw error
        if current_user.id != course.teacher_id:
            flask.abort(make_response(jsonify(errors=errors.ERR_NOT_ALLOWED), 400))

        # Edit course
        course.edit(**validated_data)

        return schema.CourseSchema(many=False).dump(course)

    if request.method == 'DELETE':

        """ Delete course"""

        course = models.Course.get_by_id(course_id=course_id)

        if not course:
            flask.abort(make_response(jsonify(errors=errors.ERR_NOT_ALLOWED), 400))

        # If logged in teacher didn't create the course, throw error
        if current_user.id != course.teacher_id:
            flask.abort(make_response(jsonify(errors=errors.ERR_NOT_ALLOWED), 400))

        # Update course deleted flag
        course.edit(deleted=True)

        # Edit user.course table
        user = models.User.get_by_id(user_id=current_user.id)

        if course in user.course:
            user.course.remove(course)

        return {}


@api_calls.route('/users/<int:user_id>', methods=['GET'])
@api_calls.route('/users', methods=['GET'])
def user_api(user_id=None):
    """ Get a user or all users by role"""

    # Get user role param
    validated_data = schema.RoleRequestSchema().load(flask.request.args or {})

    if user_id:
        return schema.UserSchema(many=False).dump(models.User.get_by_id(user_id))

    all_users = models.User.get_all_by_role(role=validated_data.get('role'))
    if not validated_data.get('role'):
        flask.abort(make_response(jsonify(errors=errors.ERR_ROLE_PARAM_REQUIRED), 400))

    return schema.UserSchema(many=True).dumps(all_users, indent=4)


@api_calls.route('/login', methods=['POST'])
def login_api():
    """ Login for users"""

    validated_data = schema.UserLoginRequestSchema().load(flask.request.json or {})

    # Get user data
    user = models.User.get_by_email_and_password(
        email=validated_data.get('email'),
        password=validated_data.get('password')
    )

    if not user:
        flask.abort(make_response(jsonify(errors=errors.ERR_BAD_CREDENTIALS), 400))

    user_schema = schema.UserSchema(many=False).dump(user)

    # Generate session-id and save into db
    user_schema['session-id'] = generate_and_update_user_session_key(user=user)
    models.UserSession.create(**{'user_id': user.id, 'session_id': user_schema['session-id']})

    return user_schema


@api_calls.route('/logout', methods=['POST'])
def logout_api():
    """
    Logout for users
    """
    session = models.UserSession.get_by_session_id(session_id=flask.request.headers.get('session_id'))
    if session:
        session.edit(deleted=True)

    return {}


@api_calls.route('/user/session', methods=['GET'])
def session_api():
    """ Get session for users"""

    session_id = flask.request.headers.get('session-id')
    user_session = models.UserSession \
        .get_by_session_id(session_id=session_id)
    if user_session:
        user_schema = schema.UserSchema(many=False).dump(user_session.user)
        user_schema['session-id'] = session_id
        return user_schema

    flask.abort(make_response(jsonify(errors=errors.ERR_BAD_SESSION_ID), 400))


@api_calls.route('/register', methods=['POST'])
def register_api():
    """ Registration for users"""

    validated_data = schema.UserRequestSchema().load(flask.request.json or {})

    # Check if role is correct
    if validated_data.get('role') != 'teacher' and validated_data.get('role') != 'student':
        flask.abort(make_response(jsonify(errors=errors.ERR_BAD_ROLE_REQUEST), 400))

    # Create user
    user = models.User.create(**validated_data)

    return schema.UserSchema(many=False).dump(user)


@api_calls.route('/teacher/<int:user_id>/add_course', methods=['PATCH'])
@decorators.check_session_role(models.RoleEnum.teacher)
def teacher_course_api(user_id):
    """ Add courses for teacher"""

    validated_data = schema.TeacherCourseRequestSchema().load(flask.request.json or {})

    # Get user
    user = models.User.get_by_id(user_id=user_id)

    if not user:
        flask.abort(make_response(jsonify(errors=errors.ERR_BAD_USER_ID), 400))

    # Check role
    if user.role.name != 'teacher':
        flask.abort(make_response(jsonify(errors=errors.ERR_BAD_USER_ROLE), 400))

    # Get course IDs
    new_ids = validated_data.get('course_id', [])
    existing_courses = list()
    new_courses = list()

    if new_ids:
        # Get existing course IDs
        existing_ids = [x.id for x in user.course]

        # Add new courses for user
        for course_id in ([int(x) for x in new_ids if x not in existing_ids]):

            course = models.Course.get_by_id(course_id=course_id)

            if not course:
                flask.abort(make_response(jsonify(errors=errors.ERR_BAD_COURSE_ID), 400))

            if course_id not in user.course:
                user.course.append(course)

            new_courses.append(course_id)

        for course_id in ([int(x) for x in new_ids if x in existing_ids]):
            existing_courses.append(course_id)

        # Edit user for given data
        user.edit(**validated_data)

    return {'existing_courses': existing_courses, 'new_courses': new_courses, 'schema': schema.TeacherCourseSchema(many=False).dump(user)}


@api_calls.route('/student/<int:student_id>/add_course/<int:course_id>', methods=['POST'])
@api_calls.route('/student/<int:student_id>/course/<int:course_id>', methods=['PATCH'])
@api_calls.route('/student/<int:student_id>/course/<int:course_id>/teacher/<int:teacher_id>', methods=['PATCH'])
@api_calls.route('/students/<int:student_id>/course', methods=['GET'])
@decorators.check_session_role(models.RoleEnum.teacher, models.RoleEnum.student, return_user=True)
def student_course_api(course_id, teacher_id=None, student_id=None):
    """ Add courses for student"""

    if request.method == 'POST':
        validated_data = schema.StudentCourseRequestSchema().load(flask.request.json or {})

        # Check course
        course = models.Course.get_by_id(course_id=course_id)

        if not course:
            flask.abort(make_response(jsonify(errors=errors.ERR_BAD_COURSE_ID), 400))

        # Check student
        user = models.User.get_by_id(user_id=student_id)

        if not user:
            flask.abort(make_response(jsonify(errors=errors.ERR_BAD_USER_ID), 400))

        # Check role
        if user.role.name != 'student':
            flask.abort(make_response(jsonify(errors=errors.ERR_BAD_USER_ROLE), 400))

        # Check if student was previously enrolled in the course
        existing_course = models.StudentCourse.get_course_for_user(student_id=student_id, course_id=course_id)

        if existing_course:
            flask.abort(make_response(jsonify(errors=errors.ERR_STUDENT_ALREADY_ENROLLED_IN_COURSE), 400))

        # Get all existing courses for user
        user_courses = models.StudentCourse.get_all_for_user_complete(student_id=student_id)
        # If user has more than 2 incomplete courses, raise error
        if len(user_courses) >= 2:
            flask.abort(make_response(jsonify(errors=errors.ERR_TOO_MANY_COURSES_FOR_STUDENT), 400))

        # Create student course
        user_course = models.StudentCourse.create(**{
            'course_id': course_id,
            'student_id': student_id,
            'comment': validated_data.get('comment'),

        })

        return schema.UserCourseSchema(many=False).dump(user_course)

    if request.method == 'PATCH':

        # Check student and teacher
        student = models.User.get_by_role(user_id=student_id, role='student')
        teacher = models.User.get_by_role(user_id=teacher_id, role='teacher')

        if not student and not teacher:
            flask.abort(make_response(jsonify(errors=errors.ERR_BAD_USER_ID), 400))

        # Student can add mark and comment
        if not teacher:

            validated_data = schema.EditStudentCourseRequestSchema().load(flask.request.json or {})

            user_course = models.StudentCourse.get_course_for_user(student_id=student_id, course_id=course_id)

            if not user_course:
                flask.abort(make_response(jsonify(errors=errors.ERR_BAD_COURSE_FOR_STUDENT), 400))

            user_course.edit(**validated_data)

        # Teacher can set course to complete
        else:
            validated_data = schema.EditStudentCourseRequestTeacherSchema().load(flask.request.json or {})

            user_course = models.StudentCourse.get_course_for_teacher(teacher_id=teacher_id,
                                                                      student_id=student_id,
                                                                      course_id=course_id)

            if not user_course:
                flask.abort(make_response(jsonify(errors=errors.ERR_BAD_COURSE_FOR_TEACHER), 400))

            if user_course.complete:
                flask.abort(make_response(jsonify(errors=errors.ERR_STUDENT_ALREADY_COMPLETED_THE_COURSE), 400))

            user_course.edit(**validated_data)

        return schema.UserCourseSchema(many=False).dump(user_course)

    if request.method == 'GET':
        """ Gets all student's courses"""

        student = models.User.get_by_role(user_id=student_id, role='student')

        if not student:
            flask.abort(make_response(jsonify(errors=errors.ERR_BAD_USER_ID), 400))

        courses = models.StudentCourse.get_all_for_user_complete(student_id=student_id)

        return schema.UserCourseSchema(many=True).dumps(courses, indent=4)


@api_calls.route('/students', methods=['GET'])
@decorators.check_session_role(models.RoleEnum.teacher)
def students_api():
    """ Get all students by course, date, and course status"""

    validated_data = schema.StudentsRequestSchema().load(flask.request.args or {})

    # Set default values for start and end date
    start_date = validated_data.get('start_date', date.today())
    course_id = validated_data.get('course_id', 1)
    complete = validated_data.get('complete', 0)

    students = models.StudentCourse.student_filter(
        start_date=start_date,
        course_id=course_id,
        complete=complete
    )

    response_dict = dict()

    response = list()

    for student in students:

        if course_id not in response_dict:
            response_dict[student.course.name] = {}

        response.append({
            'user': f'{student.user.name} {student.user.surname}',
            'user_id': student.user.id,
            'course_start_date': student.date_of_creation.date().strftime('%Y-%m-%d'),
            'complete': student.complete,
            'course_id': course_id,
            'course_name': student.course.name
        })

    return jsonify(response)


@api_calls.route('/teacher/<int:teacher_id>/courses', methods=['GET'])
@decorators.check_session_role(models.RoleEnum.teacher)
def teacher_courses_api(teacher_id):
    """ Get all courses for teacher"""

    teacher = models.User.get_by_id(user_id=teacher_id)

    if not teacher or teacher.role.name != 'teacher':
        flask.abort(make_response(jsonify(errors=errors.ERR_BAD_USER_ID), 400))

    # Get all courses for teacher
    teacher_courses = models.User.get_course_for_teacher(teacher_id=teacher_id)

    for teacher_course in teacher_courses:
        print(teacher_course.course)

    if not teacher_courses:
        flask.abort(make_response(jsonify(errors=errors.ERR_NO_COURSES_FOR_TEACHER), 400))

    for teacher_course in teacher_courses:
        return schema.CourseSchema(many=True).dumps(teacher_course.course, indent=4)


@api_calls.route('/student/<int:student_id>/rate_course', methods=['GET', 'POST'])
@decorators.check_session_role(models.RoleEnum.student)
def student_course_rate_api(student_id):
    """ For student mark popup"""

    if request.method == 'POST':
        validated_data = schema.ObligatoryStudentCourseRequestSchema().load(flask.request.json or {})

        unmarked_course = models.StudentCourse.get_unmarked_course(student_id=student_id)

        if not unmarked_course:
            flask.abort(make_response(jsonify(errors=errors.ERR_NO_UNMARKED_COURSES), 400))

        unmarked_course.edit(**validated_data)

        # Rate course average mark
        course = models.Course.get_by_id(course_id=unmarked_course.course_id)

        if course.average_mark == 0:
            course.edit(average_mark=validated_data.get('mark'))

        else:
            course.edit(average_mark=(course.average_mark + validated_data.get('mark')) / 2)

        return schema.UserCourseSchema(many=False).dump(unmarked_course)

    if request.method == 'GET':
        """ Gets student's last unmarked course"""

        unmarked_course = models.StudentCourse.get_unmarked_course(student_id=student_id)

        return schema.UserCourseSchema(many=False).dump(unmarked_course)


@api_calls.route('/student/courses/<int:course_id>', methods=['GET'])
@api_calls.route('/student/courses', methods=['GET'])
@decorators.check_session_role(models.RoleEnum.student, return_user=True)
def course_student_api(current_user, course_id=None):
    """ Get a course or all courses"""

    if request.method == 'GET':

        if course_id:
            return schema.CourseSchema(many=False).dump(models.Course.get_by_id(course_id))

        # Request args
        validated_data = schema.StudentCourseListRequestSchema().load(flask.request.args or {})

        # Set default values for start and end date
        course_name = validated_data.get('course_name')
        teacher_name = validated_data.get('teacher_name')

        # All courses the student in enrolled in
        all_enrolled_ids = [x.course_id for x in models.StudentCourse.get_all_for_user(student_id=current_user.id)]

        # Filter courses
        all_course_ids = [x.id for x in models.Course.get_for_student_filter(
            course_name=course_name,
            teacher_name=teacher_name)]

        course_dict = dict()

        # Get only the courses the student is not enrolled in
        for course_id in all_course_ids:
            if course_id not in all_enrolled_ids:

                course = models.Course.get_by_id(course_id=course_id)

                if course_id in course_dict:
                    course_dict[course_id] = {}

                else:
                    course_dict[course_id] = {'teacher_id': course.teacher_id,
                                              'teacher_name': f'{course.user.name} {course.user.surname}',
                                              'course_id': course_id,
                                              'course_name': course.name,
                                              'price': course.price,
                                              'average_mark': course.average_mark,
                                              'description': course.description}

        return jsonify([value for value in course_dict.values()])


@api_calls.route('/student/request_course/<int:course_id>', methods=['POST'])
@decorators.check_session_role(models.RoleEnum.student, return_user=True)
def course_request_student_api(current_user, course_id):
    """ Student course request"""

    if current_user.role.name != 'student':
        flask.abort(make_response(jsonify(errors=errors.ERR_BAD_ROLE_REQUEST), 400))

    validated_data = schema.StudentCourseRequestSchema().load(flask.request.json or {})

    course = models.Course.get_by_id(course_id=course_id)

    if not course:
        flask.abort(make_response(jsonify(errors=errors.ERR_BAD_COURSE_ID), 400))

    # Check if student is already enrolled in course
    check_course = models.StudentCourse.get_course_for_user(student_id=current_user.id, course_id=course_id)

    if check_course:
        flask.abort(make_response(jsonify(errors=errors.ERR_STUDENT_ALREADY_ENROLLED_IN_COURSE), 400))

    # Check if student has already sent a request that was accepted
    accepted_course = models.StudentCourseRequest.get_accepted_for_student(student_id=current_user.id,
                                                                           course_id=course_id)
    if accepted_course:
        flask.abort(make_response(jsonify(errors=errors.ERR_STUDENT_ALREADY_ACCEPTED_TO_COURSE), 400))

    # Set data for request table
    requested_course = models.StudentCourseRequest.create(**{'course_id': course_id,
                                                             'student_id': current_user.id,
                                                             'teacher_id': course.teacher_id,
                                                             'comment': validated_data.get('comment')})

    return schema.CourseReqSchema(many=False).dump(requested_course)


@api_calls.route('/teacher/request_course', methods=['GET'])
@api_calls.route('/teacher/request_course/<int:course_id>', methods=['POST'])
@decorators.check_session_role(models.RoleEnum.teacher, return_user=True)
def course_request_teacher_api(current_user, course_id=None):
    """ Teacher course request response"""

    if request.method == 'GET':
        """ Get all requested courses for teacher"""

        if current_user.role.name != 'teacher':
            flask.abort(make_response(jsonify(errors=errors.ERR_BAD_ROLE_REQUEST), 400))

        # Get all requested courses for teacher
        req_courses = models.StudentCourseRequest.get_all_requested_for_teacher(teacher_id=current_user.id)

        course_list = list()

        for req_course in req_courses:
            course_list.append({'course_id': req_course.course_id,
                                'student_id': req_course.student_id,
                                'teacher_id': req_course.teacher_id,
                                'comment': req_course.comment,
                                'accepted': req_course.accepted})

        return jsonify(course_list)

    if request.method == 'POST':
        """ Accept or reject students' request to attend course"""

        if current_user.role.name != 'teacher':
            flask.abort(make_response(jsonify(errors=errors.ERR_BAD_ROLE_REQUEST), 400))

        validated_data = schema.TeacherCourseAcceptRequestSchema().load(flask.request.json or {})

        req_course = models.StudentCourseRequest.accept_or_reject_request(course_id=course_id)

        if not req_course:
            flask.abort(make_response(jsonify(errors=errors.ERR_BAD_COURSE_ID), 400))

        if validated_data.get('accepted') == 1:
            # Edit accepted flag
            req_course.edit(accepted=True)

            # Check if student is already in the course
            course_check = models.StudentCourse.get_course_for_user(student_id=req_course.student_id,
                                                                    course_id=req_course.course_id)

            if course_check:
                flask.abort(make_response(jsonify(errors=errors.ERR_STUDENT_ALREADY_ENROLLED_IN_COURSE), 400))

            # Add student to course
            models.StudentCourse.create(**{'course_id': req_course.course_id,
                                           'student_id': req_course.student_id,
                                           })

            return schema.CourseReqSchema(many=False).dump(req_course)

        return {}
