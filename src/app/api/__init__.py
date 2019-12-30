from flask_restful import reqparse, abort, Resource
from flask import jsonify, request

import bank
from functools import partial
from . import io
from copy import deepcopy
import datatypes
from datetime import datetime
import database


# def abort_if_todo_doesnt_exist(todo_id):
#     if todo_id not in TODOS:
#         abort(404, message="Todo {} doesn't exist".format(todo_id))


parser = reqparse.RequestParser()
parser.add_argument('task')


def account_from_config(account_config):
    if account_config.type == 'local_account':
        return datatypes.LocalAccount.from_config(account_config)
    elif account_config.type == 'bank_account':
        return datatypes.Account.from_config(account_config)


# Todo
# shows a single todo item and lets you delete a todo item
class Account(Resource):
    def get(self, account_id):
        banking_configuration = bank.load_config(bank.env()['main_config_file'])
        db = database.load(bank.env()['database_folder'])

        account = account_from_config(banking_configuration.accounts[account_id])
        encoded_account = io.encode_account(account)
        encoded_account['balance'] = database.get_account_balance(db, account)
        return jsonify(encoded_account)


class AccountsList(Resource):
    def get(self):
        banking_configuration = bank.load_config(bank.env()['main_config_file'])
        encoded_accounts = map(
            lambda account: io.encode_account(account, include_children=False),
            list(banking_configuration.accounts.values()))
        return jsonify(list(encoded_accounts))


class AccountTransactions(Resource):
    def get(self, account_id):
        banking_configuration = bank.load_config(bank.env()['main_config_file'])
        db = database.load(bank.env()['database_folder'])

        account = account_from_config(banking_configuration.accounts[account_id])
        transactions = database.find_transactions(db, account, sort_direction=database.SortDirection.NEWEST_TRANSACTION_FIRST)
        return jsonify(list(map(io.encode_object, transactions)))


class AccountAccessCode(Resource):
    def get(self, account_id):
        banking_configuration = bank.load_config(bank.env()['main_config_file'])
        db = database.load(bank.env()['database_folder'])

        account = account_from_config(banking_configuration.accounts[account_id])
        access_code = database.get_account_access_code(db, account)
        return jsonify(io.encode_object(access_code))

    def put(self, account_id):
        banking_configuration = bank.load_config(bank.env()['main_config_file'])
        db = database.load(bank.env()['database_folder'])
        code = request.get_json()['code']

        account = account_from_config(banking_configuration.accounts[account_id])
        access_code = datatypes.AccessCode(code=code, date=datetime.utcnow(), account_id=account.id)
        database.update_account_access_code(db, account, access_code)
        return jsonify(io.encode_object(access_code))
