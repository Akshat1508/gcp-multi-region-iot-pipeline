# simulator.py
import grpc
import time
import random
import threading
import telemetry_pb2, telemetry_pb2_grpc

# ⚠️ YOU MUST REPLACE THESE WITH YOUR ACTUAL CLOUD RUN URLs!
# Remove "https://" and add ":443" at the end of each.
ENDPOINTS = [
    "telemetry-server-a-6vh5xfiuua-uc.a.run.app:443",  # Region A (us-central1)
    "telemetry-server-b-960084004456.us-east1.run.app:443",  # Region B (us-east1)
]

class IoTClient:
    def __init__(self, device_id):
        self.device_id = device_id
        import random 
        self.current_endpoint_idx = random.randint(0, len(ENDPOINTS) - 1)
        self.channel = None
        self.stub = None
        self._connect(self.current_endpoint_idx)

    def _connect(self, idx):
        endpoint = ENDPOINTS[idx]
        # 443 is the standard port for secure web traffic (HTTPS/SSL)
        self.channel = grpc.secure_channel(endpoint, grpc.ssl_channel_credentials())
        self.stub = telemetry_pb2_grpc.TelemetryServiceStub(self.channel)
        print(f"[{self.device_id}] Connected to {endpoint}")

    def _failover(self):
        """Switch to the next available regional endpoint."""
        self.current_endpoint_idx = (self.current_endpoint_idx + 1) % len(ENDPOINTS)
        print(f"[{self.device_id}] ⚡ FAILOVER → switching to endpoint {self.current_endpoint_idx}")
        self._connect(self.current_endpoint_idx)

    def send(self, temperature, lat, lon, timestamp):
        payload = telemetry_pb2.TelemetryData(
            device_id=self.device_id,
            temperature=temperature,
            latitude=lat,
            longitude=lon,
            timestamp=timestamp
        )
        try:
            # Attempt to send the data to Cloud Run
            response = self.stub.SendTelemetry(payload, timeout=3)
            return response.success
        except grpc.RpcError as e:
            print(f"[{self.device_id}] ❌ Connection failed. Triggering failover...")
            self._failover()
            return False  # Failed to send, must retry

def simulate_device(device_id):
    client = IoTClient(device_id)
    unsent_payloads = []  # Local buffer to prevent data loss during failover

    while True:
        # If the buffer is empty, generate a new reading
        if not unsent_payloads:
            temp = round(random.uniform(20, 80), 2)
            timestamp = int(time.time())
            payload = (temp, 28.6, 77.2, timestamp)
        else:
            # If there is data in the buffer, grab the oldest unsent reading
            payload = unsent_payloads.pop(0)

        # Try to send the payload
        success = client.send(*payload)
        
        # If it failed, put it back at the front of the buffer to try again
        if not success:
            unsent_payloads.insert(0, payload)
            
        time.sleep(1)

# Launch 100 concurrent device threads to simulate heavy load
NUM_DEVICES = 100
threads = []
for i in range(NUM_DEVICES):
    t = threading.Thread(target=simulate_device, args=(f"device-{i}",))
    threads.append(t)
    t.start()

for t in threads:
    t.join()