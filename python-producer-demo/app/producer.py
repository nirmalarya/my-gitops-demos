from flask import Flask, request, jsonify
from kafka import KafkaProducer
import json

app = Flask(__name__)

# Initialize Kafka producer
producer = KafkaProducer(bootstrap_servers='kfk.awsuse1.tst.edh.int.bayer.com:29300')

# API endpoint to trigger event generation
@app.route('/trigger-event', methods=['POST'])
def trigger_event():
    data = request.get_json()

    # Generate event based on data received
    event = {
        'user_id': data.get('user_id'),
        'event_type': data.get('event_type'),
        'page_id': data.get('page_id'),
        'referrer': data.get('referrer'),
        'user_agent': data.get('user_agent'),
    }

    # Send event to Kafka topic
    producer.send('app.ph-commercial.website.click.events.avro', json.dumps(event).encode('utf-8'))

    return jsonify({'message': 'Event triggered successfully'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
