# Readsb-MongoDB

The Readsb-MongoDB project is a tool designed to process the output of the JSON port from either `readsb` or `docker-adsb-ultrafeeder` and store this data in MongoDB for long-term storage. This document serves as a guide for setting up and utilizing this solution.

## Prerequisites

To use Readsb-MongoDB, you will need either a running instance of

- [readsb](https://github.com/wiedehopf/readsb) or 

- [docker-adsb-ultrafeeder](https://github.com/sdr-enthusiasts/docker-adsb-ultrafeeder). 

## Getting Started

### Run with docker compose

#### Prepare Readsb instance

Ensure that Readsb is accepting JSONSocket connections by running it with `--net-json-port=30047`
or update the environment section of `docker-compose.yaml` file of `ultrafeeder` with `- READSB_CMD+=("--net-json-port=30047")`.

#### Configure Application Settings

Create a `.env` file based on the `env.example.yaml` example, including the location of your readsb instance as follows:

`READSB_JSONPORT_URL: 'readsbjsonport://hostname_of_readsb:30047'`

#### Build and Run Docker Compose Containers

Execute `docker compose up --build -d` in your terminal. This command will build and run:

- A Python container with `app/readsb2mongo.py`.

- A MongoDB instance.

## Functionality

The application collects data from the socket of readsb, transforms it by
- Renaming keys
- Modifying types, like converting timestamp to date

Then it organizes (or groups) the data into "flights".

## MongoDB Data Structure

A unique database record is created for each flight (identified by the ICAO hex identifier). This record either appends data to an existing record or creates a new one, depending on the incoming data. If no data is received for ten minutes, a new flight is recognized.

Fields of the flight record in the MongoDB database include:

- `flight_id`: A unique identifier composed of the ICAO `hex` identifier and a timestamp of the first data received.
- `adsb_data_start` and `adsb_data_stop`: Start and end timestamps for the data collection.
- `adsb_data_count`: The count of data points collected.
- `callsign`: The callsign of the aircraft, stored as an empty array if not available.
- `adsb_data`: An array with raw ADS-B data, each item representing a snapshot of the flight's state at a specific time.


## Alternate ways

### Execution as a Standalone Python Application

Follow the steps below to run Readsb-MongoDB as a standalone Python application.

#### Requirements: mongodb and adsb

You must have a mongodb and adsb running.

#### Step 1: Configure the Environment

Set up the following environment variables correctly:

- `MONGODB_URL`: This designates the URL of your MongoDB instance (For example, `'mongodb://root:examplerootroot@hostname:port'`)

- `READSB_JSONPORT_URL`: This signifies the URL of your readsb JSON port (For example, `'readsbjsonport://hostname:port'`)

#### Step 2: Set Up Your Python Environment 

To add necessary dependencies, run the following command in your Python environment:

  python pip install -r requirements.txt

#### Step 3: Run the Application

With the environment ready, you can now execute Readsb-MongoDB using the following command:

python python3 app/readsb2mongo.py
