#!/usr/bin/env python
#
# FastAPI Kafka Producer.
# Connects to local and non-prod Kafka brokers and provides endpoints to send events.
#

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from confluent_kafka import Producer
from dotenv import load_dotenv
import hvac
import os
import json
import threading
import time
import tempfile
import logging

app = FastAPI()

class WebEvent(BaseModel):
    user_id: str
    event_type: str
    page_id: str
    referrer: str
    user_agent: str

# Load environment variables from .env file
load_dotenv()

# Set up logging for Kafka client
logging.basicConfig(level=logging.DEBUG)

# Define HashiCorp Vault address and AppRole details
vault_addr = os.getenv('VAULT_ADDR')
vault_role_id = os.getenv('VAULT_ROLE_ID')
vault_secret_id = os.getenv('VAULT_SECRET_ID')
vault_mount_point = 'kv'
vault_secret_path = 'ph-commercial-architecture/non-prod/edh'

if not vault_role_id or not vault_secret_id:
    raise ValueError("VAULT_ROLE_ID and VAULT_SECRET_ID environment variables must be set")

# Function to authenticate with Vault using AppRole
def authenticate_with_approle(vault_addr, role_id, secret_id):
    client = hvac.Client(url=vault_addr)
    auth_response = client.auth.approle.login(
        role_id=role_id,
        secret_id=secret_id
    )
    return auth_response['auth']['client_token']

# Function to renew the Vault token periodically
def renew_token_periodically(client, interval=7 * 3600):
    while True:
        time.sleep(interval)
        try:
            client.renew_self()
            print("Vault token renewed successfully")
        except Exception as e:
            print(f"Error renewing Vault token: {e}")

# Authenticate with Vault and start the token renewal thread
vault_token = authenticate_with_approle(vault_addr, vault_role_id, vault_secret_id)
vault_client = hvac.Client(url=vault_addr, token=vault_token)

renew_thread = threading.Thread(target=renew_token_periodically, args=(vault_client,))
renew_thread.daemon = True
renew_thread.start()

# Function to get HashiCorp Vault secrets
def get_vault_secrets(client, vault_mount_point, vault_secret_path):
    try:
        secrets = client.secrets.kv.v2.read_secret_version(
            path=vault_secret_path,
            mount_point=vault_mount_point
        )
        return secrets['data']['data']
    except hvac.exceptions.Forbidden as e:
        raise HTTPException(status_code=403, detail=f"Permission denied: {e}")
    except hvac.exceptions.InvalidPath as e:
        raise HTTPException(status_code=404, detail=f"Invalid path: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving secrets from Vault: {e}")

# Get the Vault secrets
secrets = get_vault_secrets(vault_client, vault_mount_point, vault_secret_path)

# Define Kafka broker host and port
kafka_broker = secrets['kafka_broker_us'] 

# Create temporary files for SSL certificates
with tempfile.NamedTemporaryFile(delete=False) as temp_cafile, \
     tempfile.NamedTemporaryFile(delete=False) as temp_certfile, \
     tempfile.NamedTemporaryFile(delete=False) as temp_keyfile:

    temp_cafile.write(secrets['ssl_ca'].encode('utf-8'))
    temp_certfile.write(secrets['ssl_cert'].encode('utf-8'))
    temp_keyfile.write(secrets['ssl_key'].encode('utf-8'))

    temp_cafile.flush()
    temp_certfile.flush()
    temp_keyfile.flush()

    # Kafka producer configuration
    conf = {
        'bootstrap.servers': kafka_broker,
        'security.protocol': 'SSL',
        'ssl.ca.location': temp_cafile.name,
        'ssl.certificate.location': temp_certfile.name,
        'ssl.key.location': temp_keyfile.name,
        'ssl.key.password': secrets['ssl_key_pass']
    }

    # Initialize Kafka producer
    producer = Producer(conf)

def test_kafka_connection():
    try:
        test_event = WebEvent(
            user_id='test_user',
            event_type='test_event',
            page_id='test_page',
            referrer='test_referrer',
            user_agent='test_user_agent'
        )
        event_data = test_event.dict()
        producer.produce('app.ph-commercial.website.click.events.avro', key='test', value=json.dumps(event_data))
        producer.flush()
        return {"message": "Test message sent successfully to Kafka"}
    except Exception as e:
        return {"error": f"Error sending test message to Kafka: {e}"}

@app.post("/")
async def trigger_event(web_event: WebEvent):
    event_data = web_event.dict()
    try:
        producer.produce('app.ph-commercial.website.click.events.avro', key='event', value=json.dumps(event_data))
        producer.flush()
        return {"message": "Event triggered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending event to Kafka: {e}")

@app.post("/test")
async def test_kafka_endpoint():
    return test_kafka_connection()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "UP"}

# clean up the temporary files
os.unlink(temp_cafile.name)
os.unlink(temp_certfile.name)
os.unlink(temp_keyfile.name)
