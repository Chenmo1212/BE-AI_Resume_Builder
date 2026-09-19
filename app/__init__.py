import os
from flask import Flask
from flask_cors import CORS
from app.errors import register_error_handlers

app = Flask(__name__)
CORS(app)

app.debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

register_error_handlers(app)

from app import routes
