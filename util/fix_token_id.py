from bson import ObjectId
from pymongo import MongoClient

DB = MongoClient("mongodb+srv://avwx-prod:tjQJ4beYyb13qGio@avwx-prod-w4lyb.azure.mongodb.net/account?retryWrites=true&w=majority")

query = {"$and": [{"tokens._id": {"$exists": False}}, {"tokens.value": {"$exists": True}}]}
for user in DB.account.user.find(query, {"tokens": 1}):
    uid, tokens = user["_id"], user["tokens"]
    print(uid)
    for i, token in enumerate(tokens):
        if "_id" not in token:
            tokens[i]["_id"] = str(ObjectId())
    DB.account.user.update_one({"_id": uid}, {"$set": {"tokens": tokens}})
