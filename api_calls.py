import flask
from flask import request, Blueprint, jsonify, make_response

import models
from core import db

import schema


api_calls = Blueprint('api_calls', __name__)


@api_calls.route('/get_info', methods=['GET', 'POST'])
def get_info_api():
    """ Create dummy db data"""

    if request.method == 'POST':
        for j in range(45):
            for user in ('Petar Petrovic', 'Uros Varicak', 'Dejan Ristic', 'Aleksa Folkman', 'Milic Vojinovic',
                         'Elena Lemonis', 'Stefan Blagojevic', 'Milos Medan', 'Nebojsa Ilic', 'Jason Statham',
                         'Pera Lozac', 'Cookie Mookie'):

                user = models.User(name=user)
                db.session.add(user)

        db.session.commit()

        return {}

    if request.method == 'GET':
        """ Get next fifty users from offset"""

        validated_data = schema.UserRequestSchema().load(flask.request.args or {})
        
        users = models.User.get_next_fifty(offset=validated_data.get('offset'))

        return schema.UserSchema(many=True).dumps(users, indent=4)



