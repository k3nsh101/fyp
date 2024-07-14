from geneticalgorithm import geneticalgorithm as ga
from pymongo import MongoClient
from datetime import datetime
from test import numpy as np

from utility_functions import compute_bess_generation, get_data, get_available_bess, write_data_to_db_many, connect

TIME_INTERVAL = 1/6 # in hours
DATABASE = "FYP"

client = connect()

def process_input(charging_cost, charging_discharging_limits, capacity_limits):
    
    #calculate the maximum cost taking the capacity_max as input
    max_cost = np.sum(charging_cost * capacity_limits[:,1])

    # Assume SOC limits are same for all batteries. To limit the 
    # number of inequality constraints
    SOC_MAX = 0.9
    SOC_MIN = 0.1

    varbound = charging_discharging_limits
    CHARGING_COST = charging_cost
    
    return max_cost, SOC_MAX, SOC_MIN, varbound, CHARGING_COST

# Genetic Algorithm
def cost_function(P, required_power, max_cost, current_soc, capacity_limits, soc_min_list, soc_max_list, CHARGING_COST):
    """
    Defines the optimization function. 

    Args:
        P - numpy array containing power of each battery
    
    Returns:
        total_cost - float. Total operating cost of battery for the instance.
    """

    penalty = 0
    current_power = np.sum(P)
    if (current_power != required_power):
        penalty += 10 * max_cost + 2 * max_cost * np.abs(required_power - current_power) * TIME_INTERVAL

    # Checking if the soc of the battery stays within limits after the dispatch
    post_soc = current_soc - P * TIME_INTERVAL / capacity_limits[:,1]

    if ((post_soc < soc_min_list).any() or (post_soc > soc_max_list).any()):
        penalty += 10 * max_cost + 2 * max_cost * np.abs(required_power - current_power) * TIME_INTERVAL
    
    total_cost = np.matmul(CHARGING_COST, np.abs(P)) * TIME_INTERVAL + penalty

    return total_cost

def lambda_handler(event, context):
    generation_count = 5
    renewable_generation_data = get_data(client, DATABASE, "generation_forecast", generation_count)

    vre_generation = 0
    for location in renewable_generation_data:
        vre_generation += location['wind_power'] + location['solar_power']

    vre_generation = round(vre_generation, 3)

    constant_generation = 10
    demand = round(float(get_data(client, DATABASE, "demand_forecast", 1)[0]['demand']) / 1000, 5)

    print(f"Total VRE generation: {vre_generation} MW")
    print(f"Constant generation: {constant_generation} MW")
    print(f"Demand: {demand} MW")

    required_power = round(compute_bess_generation(vre_generation, constant_generation, float(demand)), 5)

    print(f"Required BESS power: {required_power}")

    # Read the bess_info in the mongodb database
    bess_info = get_data(client, DATABASE, "bess_info")

    available_bess, charging_cost, charging_discharging_limits, capacity_limits, soc_min_list, soc_max_list, current_soc = get_available_bess(bess_info)

    for battery in available_bess:
        print(battery)

    max_cost, SOC_MAX, SOC_MIN, varbound, CHARGING_COST = process_input(charging_cost, charging_discharging_limits, capacity_limits)

    algorithm_param = {
    'max_num_iteration': 1000,
    'population_size':200,
    'mutation_probability':0.7,
    'elit_ratio': 0.01,
    'crossover_probability': 0.5,
    'parents_portion': 0.3,
    'crossover_type':'uniform',
    'max_iteration_without_improv':None
    }

    model = ga(function=cost_function, 
            dimension=len(available_bess), 
            variable_type='real', 
            variable_boundaries=varbound, 
            algorithm_parameters=algorithm_param, 
            convergence_curve=False)

    model.run()

    # Process solution

    solution = model.output_dict
    print(solution)
    optimum_power = solution['variable']
    total_cost = np.matmul(CHARGING_COST, np.abs(optimum_power)) * TIME_INTERVAL
    print(f"Total cost is: {total_cost}")

    calculated_power = solution['variable']

    post_soc = np.round(current_soc - calculated_power * TIME_INTERVAL / capacity_limits[:,1], decimals=3)

    calculated_dispatch_info = []

    for i in range(len(available_bess)):
        battery = {}
        battery['date_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        battery['id'] = available_bess[i]['index']
        # battery['index'] = available_bess[i]['index']
        battery['required_power'] = round(calculated_power[i],4)
        battery['post_soc'] = post_soc[i]

        calculated_dispatch_info.append(battery)
    
    for battery in calculated_dispatch_info:
        print(battery)

    write_data_to_db_many(client, DATABASE, "dispatch_info", calculated_dispatch_info)
    print(f"Successfully added {calculated_dispatch_info}")
