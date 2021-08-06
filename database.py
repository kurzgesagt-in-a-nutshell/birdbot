import pymongo
import dotenv
import dns
import os
import logging

dotenv.load_dotenv()
logger = logging.getLogger('Database')
try:
    db_key = os.environ.get('DB_KEY')
    client = pymongo.MongoClient(db_key)
    db = client.KurzBot
    infraction_db = db.Infraction
    timed_actions_db = db.TimedAction
    topics_db = db.Topics
    logger.info('Connected to mongoDB')

except KeyError:
    logger.error('Database key not found. Check your .env file')
