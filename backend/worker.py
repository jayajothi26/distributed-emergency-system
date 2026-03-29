import pika
import json
import time
import redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)
def process_emergency(ch, method, properties, body):
    alert = json.loads(body)
    incident_id = alert['id']
    
    # 1. Update status to "Processing" in Redis
    r.set(f"incident:{incident_id}:status", "dispatched")
    print(f" [!] Incident {incident_id} marked as DISPATCHED in Redis")

    # 2. Simulate work
    time.sleep(3) 
    
    # 3. Update status to "Resolved" in Redis
    r.set(f"incident:{incident_id}:status", "resolved")
    print(f" [v] Incident {incident_id} marked as RESOLVED in Redis")
    
    ch.basic_ack(delivery_tag=method.delivery_tag)

def start_worker():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()

    channel.queue_declare(queue='emergency_tasks')
    
    # Don't give a worker more than one message at a time
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='emergency_tasks', on_message_callback=process_emergency)

    print(' [*] Worker is online. Waiting for emergencies. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == "__main__":
    start_worker()