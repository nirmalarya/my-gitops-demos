from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer
from dotenv import load_dotenv
import hvac
import os
import json
import threading
import time
import tempfile

app = FastAPI()

class WebEvent(BaseModel):
    user_id: str
    event_type: str
    page_id: str
    referrer: str
    user_agent: str

# Load environment variables from .env file
load_dotenv()

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
        # Read the secrets from the Vault KV path
        secrets = client.secrets.kv.v2.read_secret_version(
            path=vault_secret_path,
            mount_point=vault_mount_point
        )
        return secrets['data']['data']  # Return the secrets data
    except hvac.exceptions.Forbidden as e:
        raise HTTPException(status_code=403, detail=f"Permission denied: {e}")
    except hvac.exceptions.InvalidPath as e:
        raise HTTPException(status_code=404, detail=f"Invalid path: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving secrets from Vault: {e}")

# Get the Vault secrets
secrets = get_vault_secrets(vault_client, vault_mount_point, vault_secret_path)

# Create temporary files for SSL certificates
temp_cafile = tempfile.NamedTemporaryFile(delete=False)
temp_certfile = tempfile.NamedTemporaryFile(delete=False)
temp_keyfile = tempfile.NamedTemporaryFile(delete=False)

try:
    with open(temp_cafile.name, 'w') as cafile, open(temp_certfile.name, 'w') as certfile, open(temp_keyfile.name, 'w') as keyfile:
        cafile.write(secrets['ssl_ca'])
        certfile.write(secrets['ssl_cert'])
        keyfile.write(secrets['ssl_key'])

    # Define the Kafka broker and SSL configuration
    kafka_host = 'kfk.awsuse1.tst.edh.int.bayer.com:29300'

    # Initialize Kafka producer with SSL configuration
    producer = KafkaProducer(
        bootstrap_servers=kafka_host,
        security_protocol='SSL',
        ssl_cafile=temp_cafile.name,
        ssl_certfile=temp_certfile.name,
        ssl_keyfile=temp_keyfile.name,
        ssl_password=secrets['ssl_key_pass']
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

finally:
    # Clean up temporary files
    os.unlink(temp_cafile.name)
    os.unlink(temp_certfile.name)
    os.unlink(temp_keyfile.name)
