import flask_restful

from flask import Flask, request, current_app
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

from flask_script import Manager


from sqlalchemy.exc import IntegrityError

import schema

from marshmallow import validate

from flask_migrate import Migrate, MigrateCommand

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://fww:fww2020@localhost/fww3_db'
db = SQLAlchemy(app)

cors = CORS(reseources={r"/public/*": {"origins": "*"}})

ma = Marshmallow()

# redis_store = FlaskRedis()
flask_api = Api()

# Init Marshmellow
ma.init_app(app)

# Init Cors
cors.init_app(app)

# Init App
flask_api.init_app(app)

manager = Manager(app)
migrate = Migrate(app, db)

manager.add_command('db', MigrateCommand)

from api_calls import api_calls

app.register_blueprint(api_calls)


# print('URLS', app.url_map)


if __name__ == '__main__':
    # manager.run()
    app.run(debug=True, host="0.0.0.0")
