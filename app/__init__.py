import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask import Flask, request, current_app
from config import Config
from flask_sqlalchemy import SQLAlchemy #ORM module
from flask_migrate import Migrate #DB migrations
from flask_login import LoginManager #Users logging in
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment #timezone
from flask_babel import Babel, lazy_gettext as _l #i18n and l10n support
import os
from elasticsearch import Elasticsearch
from redis import Redis
import rq

# use SQLAlchemy for database management
db = SQLAlchemy()

# use flask_migrate for migration
migrate = Migrate()

# use Flask-Login for logging-in initialization
login = LoginManager()

# set an entrypoint for user
login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.')

# use Flask-Mail for email notification etc
mail = Mail()

# use flask_boostrap for enabling bootstrap
bootstrap = Bootstrap()

#use flask_moment for timezone conversion
moment = Moment()

#use flask_babel for gettext translation etc
babel = Babel()

def create_app(config_class = Config):
    '''application factory for building app instances'''
    # initiate the Flask app
    app = Flask(__name__)

    # use config.py for configuration
    app.config.from_object(Config)

    # init all instances from above
    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app)

    # init elasticsearch instance
    app.elasticsearch = Elasticsearch([app.config['ELASTICSEARCH_URL']]) \
        if app.config['ELASTICSEARCH_URL'] else None

    # init RQ
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('microblog-tasks', connection = app.redis)

    # blueprint reg for errors module
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    # blueprint reg for auth module. 
        # url_prefix needs to change path to scheme like
        # eg: 'login' to 'auth.login' etc.
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix = '/auth')

    # blueprint reg for main module
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # blueprint reg for API module
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix = '/api')

    if not app.debug and not app.testing:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], 
                        app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            #create mail server
            mail_handler = SMTPHandler(
                mailhost = (app.config['MAIL_SERVER'], app.config['MAIL_PORT']), 
                fromaddr = 'no-reply@' + app.config['MAIL_SERVER'], 
                toaddrs = app.config['ADMINS'], 
                subject = 'Microblog failure',
                credentials = auth,
                secure = secure
            )
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

        if not os.path.exists('logs'):
            os.mkdir('logs')

        #create log journal
        file_handler = RotatingFileHandler(
            'logs/microblog.log',
            maxBytes = 10240,
            backupCount = 10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s \
            [in %(pathname)s:%(lineno)d]'
        ))

        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Microblog startup')

    return app

@babel.localeselector
def get_locale():
    '''set Accept-Languages HTTP header from config'''
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])
    #return 'ru'

from app import models
