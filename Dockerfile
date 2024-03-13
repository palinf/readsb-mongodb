# Use an official Python runtime as a parent image
FROM python:3.9.6

# Working directory to /app
WORKDIR /app

ADD requirements.txt /

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /requirements.txt

ADD app /app

# Run readsb2mongo.py when the container launches
CMD ["python", "/app/readsb2mongo.py"]

