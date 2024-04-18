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

print('hello Nik and Sam')

# Initialize Kafka producer globally 
producer = KafkaProducer(bootstrap_servers='kfk.awsuse1.tst.edh.int.bayer.com:29300')

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
