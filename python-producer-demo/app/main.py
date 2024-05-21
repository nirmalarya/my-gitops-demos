# Description: Python FastAPI application to send events to Kafka topic
from fastapi import FastAPI, HTTPException 
from pydantic import BaseModel
from kafka import KafkaProducer
import hvac
import os
import json

app = FastAPI()

class WebEvent(BaseModel):
    user_id: str
    event_type: str
    page_id: str
    referrer: str
    user_agent: str

# Define HashiCorp Vault address and KV path
vault_addr = 'https://vault.agro.services'
vault_kv_path = 'kv/ph-commercial-architecture/non-prod/edh/'
vault_token = ''

# # Get the Vault token from environment variable
# vault_token = os.getenv('VAULT_TOKEN')
# if not vault_token:
#     raise ValueError("VAULT_TOKEN environment variable is not set")

# Function to get HashiCorp Vault secrets
def get_vault_secrets(vault_addr, vault_token, vault_kv_path):
    try:
        # Initialize the Vault client
        client = hvac.Client(url=vault_addr, token=vault_token)

        # Read the secrets from the Vault KV path
        secrets = client.secrets.kv.v2.read_secret_version(
            path=vault_kv_path
        )

        return secrets['data']['data']  # Return the secrets data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving secrets from Vault: {e}")

# Get the Vault secrets
secrets = get_vault_secrets(vault_addr, vault_token, vault_kv_path)

# Define the Kafka broker and SSL configuration
kafka_host = 'kfk.awsuse1.tst.edh.int.bayer.com:29300'
ssl_cafile = secrets['ssl_ca']
ssl_certfile = secrets['ssl_cert']
ssl_keyfile = secrets['ssl_key']
ssl_password = secrets['ssl_key_pass']

# Initialize Kafka producer with SSL configuration
producer = KafkaProducer(
    bootstrap_servers=kafka_host,
    security_protocol='SSL',
    ssl_cafile=ssl_cafile,
    ssl_certfile=ssl_certfile,
    ssl_keyfile=ssl_keyfile,
    ssl_password=ssl_password
)

def test_kafka_connection():
    try:
        # Send a test message to the Kafka topic
        test_event = WebEvent(
            user_id='test_user',
            event_type='test_event',
            page_id='test_page',
            referrer='test_referrer',
            user_agent='test_user_agent'
        )
        event_data = test_event.dict()
        producer.send('app.ph-commercial.website.click.events.avro', json.dumps(event_data).encode('utf-8'))
        return {"message": "Test message sent successfully to Kafka"}
    except Exception as e:
        return {"error": f"Error sending test message to Kafka: {e}"}

@app.post("/app-pythonproducer-demo/")
async def trigger_event(web_event: WebEvent):
    event_data = web_event.dict()
    # Send event to Kafka topic
    producer.send('app.ph-commercial.website.click.events.avro', json.dumps(event_data).encode('utf-8'))
    return {"message": "Event triggered successfully"}

@app.post("/app-pythonproducer-demo/test")
async def test_kafka_endpoint():
    return test_kafka_connection()
