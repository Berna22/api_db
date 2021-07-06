import marshmallow

import models
from core import ma


###################
# REQUEST SCHEMAS #
###################

class UserRequestSchema(ma.Schema):
    offset = marshmallow.fields.Int(required=True)


# ####################
# # RESPONSE SCHEMAS #
# ####################


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = models.User
