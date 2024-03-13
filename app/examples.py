from pymongo import MongoClient, DESCENDING
from bson import json_util

## Connection to the database
client = MongoClient("mongodb://root:examplerootroot@10.90.1.1:27017")
flights_collection = client["adsb"]["flights"]

def get_last_flight():
    """
    This method is used to retrieve the last flight document in the "flights" collection.

    Return:
        dict: The last flight in the "flights" collection.
    """
    last_flight = flights_collection.find_one()
    return last_flight

# print(json_util.dumps(get_last_flight(), indent=2))


def get_last_10_flights():
    """
    This method is used to get the last 10 documents from the "flights" collection without the 'adbs_data' field.

    Return:
        list: List of last 10 flight documents without the 'adbs_data' field.
    """
    pipeline = [
        {"$sort": {"_id": DESCENDING}},
        {"$limit": 10},
        {"$project": {"adsb_data": 0}}
    ]
    cursor = flights_collection.aggregate(pipeline)
    return list(cursor)

# print(json_util.dumps(get_last_10_flights(), indent=2))

def get_last_10_flights_simple():
    """
    This method provides a simplified way to get the last 10 flights from the "flights" collection.
    It includes 'call-sign', 'hex' and count of 'adsb_data'.

    Return:
        list: List of last 10 flight documents with 'call-sign', 'hex', 'adsb_data_count'.
    """

    pipeline = [
        {"$sort": {"_id": DESCENDING}},
        {"$limit": 10},
        {"$unwind": "$adsb_data"},
        {"$group": {"_id": {"callsign": "$callsign", "hex": "$hex"}, "adsb_data_count": {"$sum": 1}}},
        {"$project": {"_id": 0, "callsign": "$_id.callsign", "hex": "$_id.hex", "adsb_data_count": 1}}
    ]
    cursor = flights_collection.aggregate(pipeline)
    return list(cursor)

#print(json_util.dumps(get_last_10_flights_simple(), indent=2))


def get_flights_entering_fence(lat1_, lat2_, lon1_, lon2_):
    """
    The method fetches flight documents in which their 'lat' and 'lon' within specified 'fence' values.

    Params: 
        lat1_ :float
        lat2_ :float
        lon1_ :float 
        lon2_ :float  

    Return:
        list: List of flight documents inside the specified fence values.
    """

    # Ensure lat1 and lat2 are correctly ordered
    lat1, lat2 = sorted(lat1_,lat2_)
    lon1, lon2 = sorted(lon1_,lon2_)

    pipeline = [
        # Match records where lat and lon are within the fence
        {
            "$match": {
                "adsb_data": {
                    "$elemMatch": {
                        "$and": [
                            {"lat": {"$gte": lat1, "$lte": lat2}},
                            {"lon": {"$gte": lon1, "$lte": lon2}}
                        ]
                    }
                }
            }


        },
        {
            "$project": {
                "flight_id": 1,  
                "hex": 1,  
                "adsb_data_start": 1,  
                "adsb_data_stop": 1,  
                "adsb_data_count": 1,  
                "callsign": 1,  
                "adsb_data": 0  # Exclude adsb_data
            }
        }

    ]
    cursor = flights_collection.aggregate(pipeline)
    return list(cursor)

#print(json_util.dumps(get_last_flight(), indent=2))




