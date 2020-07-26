import pymongo
import dns

client = pymongo.MongoClient("mongodb+srv://slothonmeth1:kbotdbpass@kbot.9nvha.mongodb.net/kbot?retryWrites=true&w=majority")
db = client.KurzBot

infraction_db = db.Infraction
