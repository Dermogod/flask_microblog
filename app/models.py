from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from hashlib import md5
from time import time
import jwt
from flask import current_app
from app import db, login
from app.search import add_to_index, remove_from_index, query_index
import json
from time import time

# "cls" stands for the 1st argument to class methods
# @classmethod is assigned to class and 
# can use class properties within method code
class SearchableMixin(object):
	@classmethod
	def search(cls, expression, page, per_page):
		ids, total = query_index(cls.__tablename__, expression, page, 
			per_page)
		if total == 0:
			return cls.query.filter_by(id = 0), 0
		when = []
		for i in range(len(ids)):
			when.append((ids[i], i))
		return cls.query.filter(cls.id.in_(ids)).order_by(
			db.case(when, value = cls.id)), total

	@classmethod
	def before_commit(cls, session):
		session._changes = {
			'add': list(session.new),
			'update': list(session.dirty),
			'delete': list(session.deleted)
		}

	@classmethod
	def after_commit(cls, session):
		'''apply session changes to ElasticSearch'''
		for obj in session._changes['add']:
			if isinstance(obj, SearchableMixin):
				add_to_index(obj.__tablename__, obj)
		for obj in session._changes['update']:
			if isinstance(obj, SearchableMixin):
				add_to_index(obj.__tablename__, obj)
		for obj in session._changes['delete']:
			if isinstance(obj, SearchableMixin):
				remove_from_index(obj.__tablename__, obj)
		session._changes = None

	@classmethod
	def reindex(cls):
		for obj in cls.query:
			add_to_index(cls.__tablename__, obj)

# SQLAlchemy events listener function registration for the given target
# listen(<target>, <identifier>, <method>)
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)

# assistive table
followers = db.Table(
	'followers',
	db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
	db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
	'''users table. UserMixin imports Flask-Login requirements'''
	id = db.Column(db.Integer, primary_key = True)
	username = db.Column(db.String(64), index = True, unique = True)
	email = db.Column(db.String(120), index = True, unique = True)
	password_hash = db.Column(db.String(128))
	about_me = db.Column(db.String(140))
	last_seen = db.Column(db.DateTime, default = datetime.utcnow)
	#one-to-many relationship
	posts = db.relationship('Post', backref = 'author', lazy = 'dynamic')
	#many-to-many relationship
	followed = db.relationship(
		'User', 
		secondary = followers, #configures association table
		primaryjoin = (followers.c.follower_id == id),
		secondaryjoin = (followers.c.followed_id == id),
		backref = db.backref('followers', lazy = 'dynamic'),
		lazy = 'dynamic' 
	) 

	messages_sent = db.relationship(
		'Message',
		foreign_keys = 'Message.sender_id',
		backref = 'author', 
		lazy = 'dynamic'
	)

	messages_received = db.relationship(
		'Message',
		foreign_keys = 'Message.recipient_id',
		backref = 'recipient',
		lazy = 'dynamic'
	)

	last_message_read_time = db.Column(db.DateTime)
	
	notifications = db.relationship(
		'Notification',
		backref = 'user',
		lazy = 'dynamic'
	)

	def __repr__(self):
		'''this method tells how to print users'''
		return '<User {} -- {}>'.format(self.username, self.email)

	def set_password(self, password):
		self.password_hash = generate_password_hash(password)

	def check_password(self, password):
		return check_password_hash(self.password_hash, password)

	def avatar(self, size):
		digest = md5(self.email.lower().encode('utf-8')).hexdigest()
		return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
			digest, size)

	def follow(self, user):
		if not self.is_following(user):
			self.followed.append(user)

	def unfollow(self, user):
		if self.is_following(user):
			self.followed.remove(user)

	def is_following(self, user):
		return self.followed.filter( 
			followers.c.followed_id == user.id ).count() > 0

	def followed_posts(self):
		'''show posts of user`s followings and his/her own, too'''
		followed =  Post.query.join(
			followers, (followers.c.followed_id == Post.user_id)).filter(
				followers.c.follower_id == self.id)

		own = Post.query.filter_by(user_id = self.id)
		return followed.union(own).order_by(Post.timestamp.desc())

	def get_reset_password_token(self, expires_in = 600):
		'''get jwt token to reset pass'''
		return jwt.encode(
			{'reset_password': self.id, 'exp': time() + expires_in}, 
			current_app.config['SECRET_KEY'],
			algorithm = 'HS256'
		).decode('utf-8')

	def new_messages(self):
		'''define unread messages by the last read time and return 
		their amount'''
		last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
		return Message.query.filter_by(recipient = self).filter(
			Message.timestamp > last_read_time).count()

	def add_notification(self, name, data):
		'''add new notification and upgrade one with same name'''
		self.notifications.filter_by(name = name).delete()
		n = Notification(name=name, payload_json=json.dumps(data), user=self)
		db.session.add(n)
		return n

	@staticmethod
	def verify_reset_password_token(token):
		try:
			id = jwt.decode(
				token, 
				current_app.config['SECRET_KEY'], 
				algorithms = ['HS256']
			)['reset_password']
		except:
			return
		return User.query.get(id)

class Post(SearchableMixin, db.Model):
	"""posts table"""
	__searchable__ = ['body'] # this field will be indexed

	id = db.Column(db.Integer, primary_key = True)
	body = db.Column(db.String(140))
	timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	language = db.Column(db.String(5))

	def __repr__(self):
		return '< Post '"{}"'>'.format(self.body)

class Message(db.Model):
	'''private messages table'''
	__tablename__ = 'messages'

	id = db.Column(db.Integer, primary_key = True)
	sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	body = db.Column(db.String(280))
	timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)

	def __repr__(self):
		return '<Message {}>'.format(self.body)

class Notification(db.Model):
	__tablename__ = 'notifications'

	id = db.Column(db.Integer, primary_key = True)
	name = db.Column(db.String(128), index = True)
	user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
	timestamp = db.Column(db.DateTime, index = True, default = datetime.utcnow)
	payload_json = db.Column(db.Text)

	def get_data(self):
		return json.loads(str(self.payload_json))

@login.user_loader
def load_user(id):
	'''reloads a user from the session'''
	return User.query.get(int(id))