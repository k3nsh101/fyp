import os

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import tensorflow as tf
import numpy as np

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
      
def get_data(client, database, collection, limit_value=None):
    db = client[f"{database}"]
    collection = db[f"{collection}"]

    if (limit_value is not None):
        return list(collection.find().sort([('$natural',-1)]).limit(limit_value))
    else:
        return list(collection.find())

def write_data_to_db(client, database, collection, data):
    db = client[f"{database}"]
    collection = db[f"{collection}"]   
    collection.insert_one(data)

def windowed_dataset(series, window_size, shift):
    """Uses an input model to generate predictions on data windows

    Args:
      series (array of float) - contains the values of the time series
      window_size (int) - the number of time steps to include in the window
      batch_size (int) - the batch size

    Returns:
      forecast (numpy array) - array containing predictions
    """

    # Generate a TF Dataset from the series values
    dataset = tf.data.Dataset.from_tensor_slices(series)

    # Window the data but only take those with the specified size
    dataset = dataset.window(window_size, shift=shift, drop_remainder=True)

    # Flatten the windows by putting its elements in a single batch
    dataset = dataset.flat_map(lambda w: w.batch(window_size))

    # Create batches of windows
    batch_size = 1
    dataset = dataset.batch(batch_size).prefetch(1)

    return dataset
