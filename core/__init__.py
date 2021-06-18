from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy as FlaskSQLAlchemy
from flask import Flask, request, current_app
from flask_cors import CORS

cors = CORS(reseources={r"/public/*": {"origins": "*"}})

db = FlaskSQLAlchemy()
ma = Marshmallow()


def create_app(app):
    """
    Method used to create flask application. It will setup logger, CORS, Session, Redis, json serialization,
    blueprints, and default data cleaners
    :param name:
    :param config_path: path to JSON configuration
    :return: configured flask app
    :rtype Flask
    """

    # Init Sqlalchemy
    db.init_app(app)

    # Init Marshmellow
    ma.init_app(app)

    # Init Cors
    cors.init_app(app)

    @app.before_request
    def before_request():
        if request.method == 'OPTIONS' or '/static/' in request.path or "/apple-app-site-association" in request.path:
            return

        if request.method != 'GET':
            current_app.logger.info("[REQUEST - {}] - URL: {}, arguments: {}, json: {}".format(
                request.method, request.base_url, request.values, request.json))

    @app.after_request
    def after_request(response):
        db.session.commit()
        if request.method != 'GET':
            current_app.logger.info("[RESPONSE] - URL: {}, response: {}".format(request.base_url, response.get_data()))
        return response

    return app
