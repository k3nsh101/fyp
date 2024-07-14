import os
import requests
import math
from datetime import datetime
from datetime import timedelta

from utility_functions import connect, write_data_to_db_many

API_KEY = os.environ["API_KEY"]
DATABASE = "FYP"
COLLECTION = "generation_forecast"


base_url = "https://api.solcast.com.au/data/forecast/radiation_and_weather"
api_parameters = "hours=1&output_parameters=air_temp,ghi,wind_speed_100m&period=PT10M&format=json"

# Wind locations
vavniya = {
    'id': 0,
    'type': 'wind',
    'latitude': 8.854314,
    'longitude': 80.506397
}   

mannar = {
    'id': 1,
    'type': 'wind',
    'latitude': 9.021706,
    'longitude': 79.834858
}


# Solar locations
hambanthota_1 = {
    'id': 2,
    'type': 'solar',
    'latitude': 6.23258,
    'longitude': 81.078728
}

welikanda = {
    'id': 3,
    'type': 'solar',
    'latitude': 7.975585,
    'longitude': 81.236128
}

hambanthota_2 = {
    'id': 4,
    'type': 'solar',
    'latitude': 6.227748,
    'longitude': 81.081328
}

locations = [vavniya, mannar, hambanthota_1, welikanda, hambanthota_2]

write_data = []

def process_weather_data(data):
    date_time = data['period_end'].split('.')[0].replace('T',' ')
    temperature = data['air_temp']
    irradiance = data['ghi']
    wind_speed = data['wind_speed_100m']

    return date_time, temperature, irradiance, wind_speed

def calculate_wind_power(windspd):
    
    #height correction 
    #standard friction coefficient = 1/7 and height is adjusted to 50m
  
    if windspd < 3:
        p = 0
    elif windspd > 3 and windspd <= 5:
        p = 3.8*(windspd**2) - 17.9*(windspd) + 24.5
    elif windspd > 5 and windspd <= 7:
        p = 6*(windspd**2) - 41*(windspd) + 85
    elif windspd > 7 and windspd <= 9:
        p = 6*(windspd**2) - 44*(windspd) + 106
    elif windspd > 9 and windspd <= 11:
        p = -5.6*(windspd**2) + 160.4*(windspd) - 794
    elif windspd > 11 and windspd <= 13:
        p = -6.1*(windspd**2) + 167.5*(windspd) - 811.6
    elif windspd > 13 and windspd <= 25:
        p = 335
    else:
        p = 0

    #return power
    return round(100*p/1000,2)

def calculate_solar_power(irr, temp):
    #cell temperature - Tc
    #ambient temperature - temp
    #irradiance - irr
    #Gnoct = 800
    #Tnoct - 46
    #Pref - 335w
    #no of panels in the plant - 100
    #alpha - 0.00042
    #beta - (-0.00304)
    #gamma - (-0.0043)
    #delta - 0.75
    #tref - 25
    
    tc = temp + (irr/800)*(46 - 20)  #calculating cell temeperature
    
    if irr == 0 :
        p = 0
    else:
        lnGoverGref = math.log(irr/1000,math.e)
        p = 20000*350 * (irr/1000)*(1+0.00042*(tc - 25))*(1 + 0.0043*(tc - 25))*(1 + 0.75*(lnGoverGref))
        p = 0 if p < 0 else p
    
    #return power
    return round(p/1000000,2)

def lambda_handler(event, context):
    for location in locations:
        api_url = f"{base_url}?latitude={location['latitude']}&longitude={location['longitude']}&api_key={API_KEY}&{api_parameters}"
        response = requests.get(api_url)
        data = response.json()['forecasts'][0]
        
        date_time, temperature, irradiance, wind_speed = process_weather_data(data)

        adjusted_date = (datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')

        data = {}

        print(f"At {location['id']} at {adjusted_date}")
        if location['type'] =='wind':
            wind_generation = calculate_wind_power(wind_speed)

            data = {
                'location': location['id'],
                'type': 'wind',
                'date_time': adjusted_date,
                'wind_power': wind_generation,
            }
            print(f"Wind power generation: {wind_generation} kW")

        if location['type'] == 'solar':
            solar_generation = calculate_solar_power(irradiance, temperature)
            print(f"Solar power generation: {solar_generation} kW")
         
            data = {
                'location': location['id'],
                'type': 'solar',
                'date_time': adjusted_date,
                'solar_power': solar_generation
            }

        write_data.append(data)

    try:
        mongoClient = connect()
        write_data_to_db_many(mongoClient, DATABASE, COLLECTION, write_data)
        print(f"Successfully added {write_data} to collection {COLLECTION}")
    except Exception as e:
        print("Failed to insert data to generation_forecast collection")
        print(e)

    
