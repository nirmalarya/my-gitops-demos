# Use the official Python image as a base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app files into the container
COPY producer.py .

# Expose the port on which FastAPI runs (optional if not needed)
# EXPOSE 5000

# Command to run the FastAPI app using the built-in development server
CMD ["uvicorn", "producer:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]