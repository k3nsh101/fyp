import tensorflow as tf
from pickle import load
import pandas as pd

from utility_functions import connect, get_data, windowed_dataset, write_data_to_db

DATABASE = "FYP"
FROM_DATABASE = "demand"
TO_DATABASE = "demand_forecast"

client = connect()

def lambda_handler(event, context):
    # Input data to the prediction model
    try:
        input_data = get_data(client, DATABASE, FROM_DATABASE, 144)
        # reverse the list to get the data in the correct order
        input_data = input_data[::-1]
    except Exception as e:
        print(e)

    # Process the data input

    df = pd.DataFrame(input_data, columns=['date_time','demand'])
    df['date_time'] = pd.to_datetime(df['date_time'])

    # Predicted time
    date = (df['date_time'].iloc[-1] + pd.Timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')

    # Preprocessing for forecasting using ML
    df['weekday'] = (df['date_time'].dt.day_of_week > 4).map({True:0, False:1})
    data_copy = df.drop(columns=['date_time'], axis=1)

    scalerfile = 'scaler.sav'
    scaler = load(open(scalerfile, 'rb'))

    scaled_data = pd.DataFrame(scaler.transform(data_copy), columns=data_copy.columns)

    # Generate the dataset windows

    window_size = 144
    shift = 1
    batch_size = 32

    dataset = windowed_dataset(scaled_data, window_size, shift)
    
    # Load the prediction model
    ckpt_path = "./model.ckpt"
    model = tf.keras.models.load_model('./model.ckpt')


    prediction = model.predict(dataset)
    denorm_prediction = prediction * (scaler.data_max_[0] - scaler.data_min_[0]) + scaler.data_min_[0]
    content = {}
    content['date_time'] = date
    content['demand'] = str(denorm_prediction[0][0])

    print(content)

    # Write the predicted demand value to the database
    try:
        write_data_to_db(client, DATABASE, TO_DATABASE, content)
        print(f"Added successfully: {content}")
    except Exception as e:
        print(e)
