from pymongo import MongoClient
import pymongo
import socket
import json
from datetime import datetime, timedelta
from collections import deque
import logging
import time
from urllib.parse import urlparse
import argparse
import os


### CHANGES
### ADD A VERSION OF THE JSON FORMAT
### Renaming of certain fields

class Readsb2Mongo:

    def __init__(self, readsb_jsonport_url, mongodb_url):
        parsed = urlparse(readsb_jsonport_url)
        self.readsb_jsonport = parsed.hostname, parsed.port

        self.mongodb_url = mongodb_url
        self.lines_processed = 0
        self.last_line_processed = ""
        self.last_time_processed = None
        self.last_ten_errors = deque(maxlen=10)

        #set db
        mongodb_parsed = urlparse(mongodb_url)
        logging.info(f"Connecting to MongoDB {mongodb_parsed.hostname}:{mongodb_parsed.port}") # added logging for MongoDB URL
        client = MongoClient(self.mongodb_url)
        db = client["adsb"]
        self.collection_db = db["adsb"]
        self.flights_collection = db["flights"]

    def insert_data(self, data):
        convert_and_rename_dict = {
            # callsign contains trailing spaces, rename flight to callsign
            "flight": ("callsign", lambda x: x.strip()),

            # convert timestamp to datetime for mongo and ease of use
            "now": ("timestamp", datetime.fromtimestamp),
            #"hex": ICAO identifier
        }

        try:
            data_dict = json.loads(data)
            #self.collection_db.insert_one(data_dict)
            self.last_time_processed = datetime.now()
        except Exception as e:
            logging.exception(e)
            self.last_ten_errors.append(str(e))

        # Rename and convert

        converted_and_renamed_data_dict = {}
        for key, value in data_dict.items():
            new_key, convert_func = convert_and_rename_dict.get(key, (key, None))
            if convert_func:
                value = convert_func(value)
            converted_and_renamed_data_dict[new_key] = value

        hex_value = converted_and_renamed_data_dict.get('hex')
        timestamp = converted_and_renamed_data_dict["timestamp"]
        callsign = converted_and_renamed_data_dict.get("callsign", None)

        logging.debug(f'Processing: {hex_value}')

        document = self.get_last_entry(hex_value)

        attach_to_existing = False
        if document:
            flight = document[0]
            flight_id = flight["flight_id"]
            # Check if the timestamp of the most recent adsb_data is not older than 10 minutes
            if flight['adsb_data']['timestamp'] >= timestamp - timedelta(minutes=10):
                attach_to_existing = True
            # Other conditions to attach to existing ?

        if attach_to_existing:
            logging.debug(f'Attaching to existing document: {flight_id} {flight["adsb_data_count"]}')
            # If document found and timestamp is recent, add the new data to the adsb_data array in the document
            self.flights_collection.update_one(
                {'flight_id': flight_id},
                {
                    '$set': {
                        'adsb_data_stop': timestamp,
                    },
                    '$inc': {
                        "adsb_data_count": 1
                    },
                    '$push': {
                        "adsb_data": converted_and_renamed_data_dict
                    },
                    '$addToSet': {
                        **({"callsign": callsign} if callsign is not None else {})
                    }
                }
            )
        else:
            logging.info(f'Document not found or timestamp too old: Creating a new one for {hex_value}')
            timestamp_str = timestamp.strftime("%y%m%d_%H%M")
            flight_id = f'{hex_value}_{timestamp_str}'


            self.flights_collection.insert_one(
                {'flight_id': flight_id,
                 'hex': hex_value,

                 'adsb_data_start': timestamp,
                 'adsb_data_stop': timestamp, # for convenience
                 'adsb_data': [converted_and_renamed_data_dict],
                 'adsb_data_count': 1,
                 **({'callsign': [callsign]} if callsign is not None else {'callsign': []}) # todo: find more elegant
                 }
            )

    def get_last_entry(self, hex_value):
        pipeline = [
            {"$match": {'hex': hex_value}},  # match the document with the provided hex value
            {"$unwind": "$adsb_data"},  # deconstructs adsb_data to output a document for each element
            {"$sort": {"adsb_data.timestamp": pymongo.DESCENDING}},  # sort by timestamp in descending order
            {"$limit": 1}  # get only the first document (most recent one)
        ]
        document = self.flights_collection.aggregate(pipeline)
        document = list(document)
        return document

    def read_and_process(self):
        while True:
            try:

                logging.info(f"connecting to readsb jsonport socket {self.readsb_jsonport}")

                s = socket.socket()
                s.connect(self.readsb_jsonport)
                logging.info("connected to socket. waiting for messages to arrive")

                for line in s.makefile('rb'):
                    self.lines_processed += 1
                    line = line.rstrip(b'\n')

                    start_time = time.time()

                    self.insert_data(line)

                    # Calculate time taken in ms and round it to one decimal place
                    elapsed_time_ms = round((time.time() - start_time) * 1000, 1)

                    # Log how long it took
                    logging.debug(f"'insert_raw_data' took {elapsed_time_ms} milliseconds")

            except Exception as e:
                logging.exception(e)
                self.last_ten_errors.append(str(e))
            logging.error("close? socket")
            time.sleep(5)  # wait for 5 seconds before retrying

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(description='Readsb2Mongo application.')

    parser.add_argument('--readsb_jsonport_url',
                        help='URL for the readsb jsonport. If not provided, it will look for READSB_JSONPORT_URL in environment variables or use the default value.')
    parser.add_argument('--mongodb_url',
                        help='URL for MongoDB. If not provided, it will look for MONGODB_URL in environment variables or use the default value.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Set log level to DEBUG if this flag is present, otherwise INFO')

    args = parser.parse_args()

    readsb_jsonport_url = args.readsb_jsonport_url if args.readsb_jsonport_url else os.getenv('READSB_JSONPORT_URL')
    mongodb_url = args.mongodb_url if args.mongodb_url else os.getenv('MONGODB_URL')

    if args.verbose or os.getenv('VERBOSE'):
        logging.info(f"VERBOSE is set, debug")
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug(f"starting connections...")

    else:
        logging.info(f"VERBOSE is not set, will progress silently ")
        logging.getLogger().setLevel(logging.INFO)

    data_processor = Readsb2Mongo(readsb_jsonport_url, mongodb_url)
    data_processor.read_and_process()