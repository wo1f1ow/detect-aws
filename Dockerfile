# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install git
RUN apt-get update && apt-get install -y git

# Copy the current directory contents into the container at /usr/src/app
COPY detect.py /usr/src/app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir boto3

# Run detect.py when the container launches, repository path must be provided as an argument
ENTRYPOINT ["python", "./detect.py"]
