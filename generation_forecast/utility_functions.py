import os

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

user_name = os.environ["USER_NAME"]
user_password = os.environ["USER_PWD"]

def connect():
    uri = f"mongodb+srv://{user_name}:{user_password}@cluster0.a5jdgea.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

    client = MongoClient(uri, server_api=ServerApi('1'))
                            
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
        return client
    except Exception as e:
        print(e)

def write_data_to_db_many(client, database, collection, data):  
    db = client[f"{database}"]
    collection = db[f"{collection}"]   
    collection.insert_many(data)

