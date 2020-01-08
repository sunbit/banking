from flask import Flask
from flask_cors import CORS
from flask_restful import Api as RestApi


from . import scheduler
from . import api


def run(banking_config):
    scheduler.run(banking_config)

    app = Flask('banking')
    rest_api = RestApi(app)
    CORS(app)

    rest_api.add_resource(api.AccountsList, '/accounts')
    rest_api.add_resource(api.Account, '/accounts/<account_id>')
    rest_api.add_resource(api.BankAccessCode, '/banks/<bank_id>/access_code')
    rest_api.add_resource(api.AccountTransactions, '/accounts/<account_id>/transactions')
    rest_api.add_resource(api.AccountAccessCode, '/accounts/<account_id>/access_code')

    app.run(debug=False, host='0.0.0.0')
