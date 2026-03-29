import pika

def send_alert_to_queue(alert_data):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    
    # Create the queue if it doesn't exist
    channel.queue_declare(queue='emergency_tasks')
    
    channel.basic_publish(exchange='',
                          routing_key='emergency_tasks',
                          body=alert_data)
    print(f" [x] Sent Alert: {alert_data}")
    connection.close()