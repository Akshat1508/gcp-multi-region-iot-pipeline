# server.py
import grpc
from concurrent import futures
import telemetry_pb2, telemetry_pb2_grpc
from google.cloud import pubsub_v1
import os

# Put your exact Project ID here
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "iot-pipeline-project-495600") 
TOPIC_ID = "telemetry-topic"

# Setup the Pub/Sub client
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

class TelemetryServicer(telemetry_pb2_grpc.TelemetryServiceServicer):
    def SendTelemetry(self, request, context):
        # Format the incoming data and forward it to the Pub/Sub queue
        data = f"{request.device_id},{request.temperature},{request.timestamp}".encode()
        publisher.publish(topic_path, data)
        
        # Send a success message back to the IoT device
        return telemetry_pb2.Ack(success=True, message="received")

def serve():
    # Create the gRPC server with a pool of 10 worker threads
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    telemetry_pb2_grpc.add_TelemetryServiceServicer_to_server(TelemetryServicer(), server)
    
    # Cloud Run assigns a port dynamically, so we must read it from the environment
    port = os.environ.get("PORT", "8080")
    server.add_insecure_port(f"[::]:{port}")
    
    print(f"Server starting on port {port}...")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()