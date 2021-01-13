from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from flask_babel import _, lazy_gettext as _l
from app.models import User

class LoginForm(FlaskForm):
	'''sign-in form on web page'''
	username = StringField(_l('Username'), validators = [DataRequired()])
	password = PasswordField(_l('Password'), validators = [DataRequired()])
	remember_me = BooleanField(_l('Remember me!'))
	submit = SubmitField(_l('Sign In'))

class RegistrationForm(FlaskForm):
	"""sign-up form on web page"""
	username = StringField(_l('Username'), validators = [DataRequired()])
	email = StringField(_l('Email'), validators = [DataRequired(), Email()])
	password = PasswordField(_l('Password'), validators = [DataRequired()])
	password2 = PasswordField(
		_l('Repeat Password'), 
		validators = [DataRequired(), EqualTo('password')]
	)
	submit = SubmitField(_l('Sign Up'))

	def validate_username(self, username):
		user = User.query.filter_by(username = username.data).first()
		if user is not None:
			raise ValidationError(_('Please use another username'))

	def validate_email(self, email):
		user = User.query.filter_by(email = email.data).first()
		if user is not None:
			raise ValidationError(_('Please use another email'))

class ResetPasswordRequestForm(FlaskForm):
	'''user sends request to reset password'''
	email = StringField(_l('Email'), validators = [DataRequired(), Email()])
	submit = SubmitField(_l('Request Password Reset'))

class ResetPasswordForm(FlaskForm):
	'''reset password'''
	password = PasswordField(_l('Password'), validators = [DataRequired()])
	password2 = PasswordField(
		_l('Repeat Password'), 
		validators = [DataRequired(), EqualTo('password')]
	)
	submit = SubmitField(_l('Request Password Reset'))


		

