from flask import Flask

from flask_script import Manager
from core import db, create_app

from flask_migrate import Migrate, MigrateCommand

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1234@localhost/api_db'

app = create_app(app)
import models

manager = Manager(app)
migrate = Migrate(app, db)

manager.add_command('db', MigrateCommand)

from api_calls import api_calls

app.register_blueprint(api_calls)


# print('URLS', app.url_map)


if __name__ == '__main__':
    # manager.run()
    app.run(debug=True, host="0.0.0.0")
