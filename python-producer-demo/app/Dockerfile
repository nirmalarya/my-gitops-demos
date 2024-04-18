# Use the official Python image as a base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app files into the container
COPY producer.py .

# Expose the port on which Flask app runs
EXPOSE 5000

# Command to run the Flask app
CMD ["python", "producer.py"]
