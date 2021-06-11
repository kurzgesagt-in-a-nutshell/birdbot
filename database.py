import pymongo
import dotenv
import dns
import os
import logging

dotenv.load_dotenv()
try:
    db_key = os.environ.get('DB_KEY')
    client = pymongo.MongoClient(db_key)
    print('connected to mongo')
    db = client.KurzBot
    infraction_db = db.Infraction
    timed_actions_db = db.TimedAction

except KeyError:
    logging.error('Database key not found. Check your .env file')



