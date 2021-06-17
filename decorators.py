from flask import make_response, jsonify

import errors

import flask
import functools


def _get_user_by_session_id():
    """
    Method is used for checking if session is valid(sessions are valid for one day only)
    :return:
    """
    # If session_id is not send return error
    session_id = flask.request.headers.get('session-id')
    if not session_id:
        flask.abort(make_response(jsonify(errors=errors.ERR_MISSING_SESSION_ID), 400))

    from models import UserSession
    # Get logged in user
    user_session = UserSession.get_by_session_id(session_id=session_id)
    if not user_session:
        flask.abort(make_response(jsonify(errors=errors.SESSION_NOT_VALID), 400))

    return user_session.user


def _check_role(role, permissions, exclude=False):
    """
    Check is role in permissions or is it excluded from permissions
    :param role:
    :param permissions:
    :param exclude:
    :return:
    """
    if not exclude and role not in permissions:
        flask.abort(make_response(jsonify(errors=errors.ERR_BAD_USER_ROLE), 403))
    if exclude and role in permissions:
        flask.abort(make_response(jsonify(errors=errors.ERR_BAD_USER_ROLE), 403))


def check_session_role(*permissions, exclude=False, return_user=False, check_role=False):
    """

    :param permissions:
    :param exclude:
    :param return_user:
    :param check_role
    :param check_pin:
    :return:
    """

    def decorator(func):
        @functools.wraps(func)
        def _decorated(*args, **kwargs):
            # Get current user if session is valid
            current_user = _get_user_by_session_id()

            if check_role:
                _check_role(role=current_user.role, permissions=permissions, exclude=exclude)

            # Return current_user if requested
            if return_user:
                response = func(current_user, *args, **kwargs)
            else:
                response = func(*args, **kwargs)

            return response

        return _decorated

    return decorator
