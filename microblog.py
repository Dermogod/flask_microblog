from app import create_app, db, cli
from app.models import User, Post, Notification, Message

# initialize application global variable
app = create_app()

# gain access to cli module
cli.register(app)

@app.shell_context_processor
def make_shell_context():
	'''default import modules for flask shell'''
	return {'db': db, 'User': User, 'Post' : Post, 'Message': Message,
        'Notification': Notification}
