from flask import Blueprint

# blueprint takes name of scheme and name of module
# (usually __name__) as arguments!
bp = Blueprint('errors', __name__) 

from app.errors import handlers