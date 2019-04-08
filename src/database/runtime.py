from tinymongo import TinyMongoClient

import re

from . import io


def load(bank_config):
    connection = TinyMongoClient('database')
    db = getattr(connection, bank_config.id)
    return db


def update_account_movements(db, fetched_movements):
    if not fetched_movements:
        return

    collection = db.account_movements

    # Get from the database all the movements starting with the
    # first one that matches the first fetched movement
    first_fetched_movement = io.find_movement(collection, fetched_movements[0])
    if first_fetched_movement is not None:
        existing_movements = io.find_movements_since(collection, first_fetched_movement)
    else:
        existing_movements = list(map(
            io.decode_movement,
            collection.find(
                {'transaction_date': {'$gte': fetched_movements[0].transaction_date}},
                sort=[('_seq', 1)]
            )
        ))

    added = 0
    updated = 0
    for action, movement in io.select_new_movements(fetched_movements, existing_movements):
        if action == 'insert':
            collection.insert_one(io.encode_movement(movement))
            added += 1
        elif action == 'update':
            collection.update({'_id': movement._id}, io.encode_movement(movement))
            updated += 1


