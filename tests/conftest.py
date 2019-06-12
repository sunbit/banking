import pytest

from tinymongo import TinyMongoClient

from database.io import encode_transaction

import tempfile


@pytest.fixture(scope='function')
def db_from_transactions():

    def make_db(**collections):
        connection = TinyMongoClient(tempfile.mkdtemp())
        test_db = getattr(connection, 'banking')
        for collection_id, transactions in collections.items():
            test_collection = getattr(test_db, collection_id)
            for transaction in transactions:
                test_collection.insert_one(encode_transaction(transaction))

        return test_db

    return make_db
