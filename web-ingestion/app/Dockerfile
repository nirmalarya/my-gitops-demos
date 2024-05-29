# Dockerfile
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI app files into the container
COPY main.py .
COPY ssl_utils.py .

# Define build arguments
ARG VAULT_ROLE_ID
ARG VAULT_SECRET_ID
ARG VAULT_ADDR

# Set environment variables based on build arguments
ENV VAULT_ROLE_ID=$VAULT_ROLE_ID
ENV VAULT_SECRET_ID=$VAULT_SECRET_ID
ENV VAULT_ADDR=$VAULT_ADDR

# Expose the port on which FastAPI runs (optional if not needed)
# EXPOSE 5000

# Command to run the FastAPI app using the built-in development server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]
