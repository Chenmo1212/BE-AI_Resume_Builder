from flask import Flask
from flask_pymongo import PyMongo
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load the appropriate configuration based on the environment
# if app.env == 'production':
#     app.config.from_object('config_production')
# else:
app.config.from_object('config_development')

app.debug = True

mongo = PyMongo(app)

from app import routes
