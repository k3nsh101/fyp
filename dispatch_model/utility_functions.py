import os

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from test import numpy as np

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

def write_data_to_db(client, database, collection, data):
    db = client[f"{database}"]
    collection = db[f"{collection}"]   
    collection.insert_one(data)

def write_data_to_db_many(client, database, collection, data):
    db = client[f"{database}"]
    collection = db[f"{collection}"]   
    collection.insert_many(data)

def get_data(client, database, collection, limit_value=None):
    db = client[f"{database}"]
    collection = db[f"{collection}"]

    if (limit_value is not None):
        return list(collection.find().sort([('$natural',-1)]).limit(limit_value))
    else:
        return list(collection.find())
    

def compute_bess_generation(vre_generation, constant_generation, demand):
    # if the calculated value is < 0, the BESS should consume power and charge.
    return demand - (vre_generation + constant_generation)

def get_available_bess(bess_info):
    available_bess= []
    charging_cost = []
    capacity_limits = []
    soc_min_list = []
    soc_max_list = []
    current_soc = []
    charging_discharging_limits = []
    
    for battery in bess_info:
        index = battery['index']
        soc_min = battery['soc_min']
        soc_max = battery['soc_max']
        soc = battery['soc']

        # Only consider batteries if the current SOC is within limits
        if (soc >= soc_min and soc <= soc_max):
            print(f"Adding battery with Index: {index}")
            available_bess.append(battery)

            charging_cost.append(battery['charging_cost'])

            charging_power_max = battery['charging_power_max']
            discharging_power_max = battery['discharging_power_max']
            charging_discharging_limits.append([-charging_power_max, discharging_power_max])

            capacity_max = battery['capacity']
            capacity_limits.append([0, capacity_max])

            soc_min_list.append(soc_min)            
            soc_max_list.append(soc_max)            
            current_soc.append(soc)
        else:
            print(f"Neglected Battery {index} because the SOC is not within the SOC limits (SOC = {soc}).")
        
    return available_bess, np.array(charging_cost), np.array(charging_discharging_limits), np.array(capacity_limits), np.array(soc_min_list), np.array(soc_max_list), np.array(current_soc)

