from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer
import json

app = FastAPI()

# Initialize Kafka producer
producer = KafkaProducer(bootstrap_servers='kfk.awsuse1.tst.edh.int.bayer.com:29300')

class WebEvent(BaseModel):
    user_id: str
    event_type: str
    page_id: str
    referrer: str
    user_agent: str

@app.post("/app-pythonproducer-demo/")
async def trigger_event(web_event: WebEvent):
    event_data = web_event.dict()

    # Send event to Kafka topic
    producer.send('app.ph-commercial.website.click.events.avro', json.dumps(event_data).encode('utf-8'))

    return {"message": "Event triggered successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)