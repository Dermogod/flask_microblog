import os
from dotenv import load_dotenv # to create .env file

basedir = os.path.abspath(os.path.dirname(__file__))

# export environment variables into system from .env file
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    '''using sqlite DB'''
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pagination options
    POSTS_PER_PAGE = 25

    # Available languages for flask-babel
    LANGUAGES = ['en','ru']

    # key for connecting with Microsoft Azure translator API
    MS_TRANSLATOR_KEY = os.environ.get('MS_TRANSLATOR_KEY')

    # enable Elasticsearch
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')

    #Enable email notifications
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['warfishe@yandex.ru']   
