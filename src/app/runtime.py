from flask import Flask
from flask_restful import Api as RestApi


from . import scheduler
from . import api


def run(banking_config):
    scheduler.run(banking_config)

    app = Flask('banking')
    rest_api = RestApi(app)

    rest_api.add_resource(api.TodoList, '/todos')
    rest_api.add_resource(api.Todo, '/todos/<todo_id>')

    app.run(debug=False, host='0.0.0.0')
