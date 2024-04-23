from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer
import json

app = FastAPI()

class WebEvent(BaseModel):
    user_id: str
    event_type: str
    page_id: str
    referrer: str
    user_agent: str

# Define Kafka broker and SSL configuration directly in code
kafka_host = 'kfk.awsuse1.tst.edh.int.bayer.com:29300'
ssl_cafile = '/path/to/ca.crt'
ssl_certfile = '/path/to/client.crt'
ssl_keyfile = '/path/to/client.key'
ssl_password = 'your_ssl_password'

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
