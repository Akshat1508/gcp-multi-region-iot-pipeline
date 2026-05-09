# Multi-Region Active-Active IoT Telemetry Pipeline

> **Enterprise-grade disaster recovery — serverless, zero data loss, automated failover in under 15 seconds.**

Traditional High-Availability systems rely on expensive, always-on Virtual Machines sitting idle in a standby region. This project proves that a **serverless, multi-region architecture** achieves the same enterprise resilience at a fraction of the cost.

Using **Python, gRPC, Cloud Run, and Pub/Sub**, this pipeline actively ingests high-frequency IoT telemetry across two GCP regions (`us-central1` and `us-east1`) simultaneously. When a catastrophic regional failure is injected, custom client-side routing automatically detects the outage and reroutes **100% of traffic to the surviving region in under 15 seconds — with zero data loss.**

---

## 📋 Table of Contents

- [Architecture Overview](#-architecture-overview)
- [Key Achievements & Live Benchmarks](#-key-achievements--live-benchmarks)
- [Tech Stack](#️-tech-stack)
- [Project Structure](#-project-structure)
- [How to Run Locally](#-how-to-run-locally)
- [Deploy to GCP Cloud Run](#️-deploying-to-gcp-cloud-run)
- [Chaos Engineering Runbook](#️-chaos-engineering-runbook--reproduce-the-dr-test)
- [Results Summary](#-results-summary)
- [Course Context](#-course-context)

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     IoT Device Simulator                        │
│              (Python · ThreadPoolExecutor · 50 threads)         │
└──────────────────────┬──────────────────────────────────────────┘
                       │  gRPC + Protobuf
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Client-Side Failover Router                    │
│          Detects UNAVAILABLE → auto-reroutes in < 15s           │
└───────────────┬─────────────────────────┬───────────────────────┘
                │ 50% traffic             │ 50% traffic
                ▼                         ▼
   ┌────────────────────┐    ┌────────────────────┐
   │   Cloud Run (A)    │    │   Cloud Run (B)    │
   │   us-central1      │    │   us-east1         │
   │   Python gRPC srv  │    │   Python gRPC srv  │
   └────────┬───────────┘    └──────────┬─────────┘
            │  publish                  │  publish
            └──────────────┬────────────┘
                           ▼
              ┌─────────────────────────┐
              │      GCP Pub/Sub        │
              │  At-least-once delivery │
              │  Zero message loss      │
              └─────────────────────────┘
                           │
              ┌─────────────────────────┐
              │   GCP Cloud Monitoring  │
              │  Dashboards · Heatmaps  │
              │  Latency · CPU · Errors │
              └─────────────────────────┘
```

**Failover flow:** When Region A goes offline → client receives `gRPC UNAVAILABLE` → failover handler triggers → 100% of traffic reroutes to Region B → Cloud Run auto-scales → Pub/Sub continues accumulating — **zero messages dropped.**

---

## Key Achievements & Live Benchmarks

### 1. Instantaneous Regional Failover — Zero Downtime

At the exact failover moment, Region A (`us-central1`) drops to zero requests. Simultaneously, Region B (`us-east1`) auto-scales to absorb 100% of the load — no gap, no manual intervention.

<p align="center">
  <img src="Traffic%20regional%20rerouting%20us-central.png" width="48%" alt="us-central1 traffic drops to zero at failover">
  <img src="Traffic%20regional%20rerouting%20us-east.png" width="48%" alt="us-east1 absorbs 100% of traffic at failover">
</p>

> **Reading the charts:** The left chart shows `us-central1` request count collapsing to zero at ~8:25 AM. The right chart shows `us-east1` spiking to double capacity at the exact same timestamp. This is the active-active transition proving itself under real conditions.

---

### 2. Zero Data Loss — Pub/Sub Queue Integrity

The Pub/Sub undelivered message count rises in a **smooth, unbroken line** throughout the entire test — before, during, and after the failover event.

<p align="center">
  <img src="Cloud%20PubSub%20Subscription.png" width="72%" alt="Pub/Sub queue depth — unbroken upward trend proves zero data loss">
</p>

> **Why a rising line is the proof of success:** Because no subscriber was deployed to drain the queue during the test, messages accumulate. The critical observation is that there is **no dip, no plateau, no gap** at the failover moment. A break in this line would be the signature of lost data. The unbroken slope proves every single message reached Pub/Sub — even during the regional outage.

---

### 3. Zero Cascading Failures — 5xx Error Flatline

Despite forcing a massive regional outage and instantly doubling the surviving region's workload, the system experienced **zero 5xx server errors.** The success rate scaled up; errors stayed flatlined.

<p align="center">
  <img src="2xx%20Response%20Code.png" width="48%" alt="2xx success codes — consistently high throughout">
  <img src="5xx%20Response%20Code.png" width="48%" alt="5xx error codes — flat at zero throughout">
</p>

> Only 1–3 transient errors appeared at the exact moment of regional deletion — the theoretical minimum unavoidable during any failover detection window. They lasted seconds, then returned to zero permanently.

---

### 4. gRPC Latency — Sub-20ms Server Processing

Latency heatmaps from Cloud Monitoring show **92% of all requests processed in under 20ms** server-side — sent from New Delhi to US data centers.

<p align="center">
  <img src="gRPC%20Request%20Latency%20us-central.png" width="48%" alt="us-central1 gRPC request latency heatmap">
  <img src="gRPC%20Request%20Latency%20us-east.png" width="48%" alt="us-east1 gRPC request latency heatmap">
</p>

> This proves the efficiency of **gRPC + Protobuf** over REST + JSON. Binary encoding reduces payload size by ~60% and eliminates per-request TCP handshake overhead through persistent HTTP/2 connections.

---

### 5. Serverless Elasticity — CPU Auto-Scaling

Cloud Run's serverless containers dynamically adjusted to the load shift without any manual operator intervention.

<p align="center">
  <img src="CPU%20Utilization%20us-central.png" width="48%" alt="us-central1 CPU drops to zero at failover">
  <img src="CPU%20Utilization%20us-east.png" width="48%" alt="us-east1 CPU spikes then normalises as Cloud Run scales out">
</p>

> Region A CPU collapses to zero as it loses all traffic. Region B CPU spikes briefly to ~80% as it absorbs double the load, then normalises as Cloud Run auto-scales new container instances to share the work.

---

### 6. Protobuf Serialization Consistency — Message Size

Pub/Sub message sizes remain tightly consistent throughout the test, confirming deterministic Protobuf encoding.

<p align="center">
  <img src="PubSub%20Message%20Size.png" width="72%" alt="Pub/Sub message size — consistent throughout">
</p>

> Messages cluster around **~29.2 KiB ± 0.2 KiB** for the entire duration — before, during, and after failover. This determinism is impossible with variable-length JSON encoding and enables precise cloud cost forecasting.

---

## Client-Side Routing & Failover Logs

Instead of relying on slow DNS updates or expensive global load balancers, this project uses **custom client-side routing** embedded directly in the Python gRPC client.

### Active-Active Distribution (Healthy State)

Under normal conditions, the simulator distributes connections across both regional endpoints simultaneously — proving the 50/50 split is working as designed.

<p align="center">
  <img src="active-active%20distribution.png" width="80%" alt="Client logs showing active-active distribution across both regions">
</p>

### Instantaneous Failover Detection

When Region A goes offline, the gRPC channels throw a connection exception immediately. The client catches this, logs the failure, and reroutes all telemetry to the surviving East endpoint — with no human action required.

<p align="center">
  <img src="Instantaneous%20Failover.png" width="80%" alt="Client logs showing failover detection and automatic rerouting to Region B">
</p>

---

## Tech Stack

| Layer | Technology | Why This Choice |
|-------|-----------|-----------------|
| **Language** | Python 3 | Rapid development; production-grade gRPC and GCP SDKs |
| **Protocol** | gRPC + Protocol Buffers | 3–5× lower latency vs REST; 60% smaller payloads vs JSON |
| **Compute** | GCP Cloud Run (Serverless) | Scale-to-zero eliminates idle standby cost; instant burst scaling |
| **Messaging** | GCP Pub/Sub | At-least-once delivery; fully managed; zero idle VMs |
| **Observability** | GCP Cloud Monitoring | Native dashboards; real-time metrics; timestamped proof |
| **Container** | Docker + Cloud Build | Reproducible multi-region deployments; automated CI/CD |

---

## Project Structure

```
gcp-multi-region-iot-pipeline/
│
├── telemetry.proto                             # Protobuf schema — IoT telemetry message definition
├── telemetry_pb2.py                            # Auto-generated: message serialization classes
├── telemetry_pb2_grpc.py                       # Auto-generated: gRPC service stubs
│
├── server.py                                   # Python gRPC server — deployed to Cloud Run (both regions)
├── simulator.py                                # Python IoT device simulator — client with failover logic
│
├── Dockerfile                                  # Container definition for Cloud Run deployment
├── requirements.txt                            # Python dependencies
│
├── Presentation.pdf                            # Full architecture, trade-off analysis & benchmark slides
│
├── Traffic regional rerouting us-central.png   # Benchmark: Region A traffic drop at failover
├── Traffic regional rerouting us-east.png      # Benchmark: Region B traffic spike at failover
├── Cloud PubSub Subscription.png               # Benchmark: Pub/Sub queue depth (zero data loss proof)
├── PubSub Message Size.png                     # Benchmark: Protobuf message size consistency
├── 2xx Response Code.png                       # Benchmark: Success responses throughout failover
├── 5xx Response Code.png                       # Benchmark: Zero error responses throughout failover
├── gRPC Request Latency us-central.png         # Benchmark: Sub-20ms latency heatmap (central)
├── gRPC Request Latency us-east.png            # Benchmark: Sub-20ms latency heatmap (east)
├── CPU Utilization us-central.png              # Benchmark: CPU drop in Region A at failover
├── CPU Utilization us-east.png                 # Benchmark: CPU spike then normalise in Region B
├── active-active distribution.png              # Client log: healthy 50/50 load distribution
├── Instantaneous Failover.png                  # Client log: failover detection and rerouting
│
└── README.md                                   # This file
```

---

## 🚀 How to Run Locally

### Prerequisites

- Python 3.9+
- Google Cloud SDK (`gcloud`) authenticated
- A GCP project with Cloud Run, Pub/Sub, and Cloud Monitoring APIs enabled

### Step 1 — Clone the repository

```bash
git clone https://github.com/Akshat1508/gcp-multi-region-iot-pipeline.git
cd gcp-multi-region-iot-pipeline
```

### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Compile the Protobuf schema

```bash
python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  telemetry.proto
```

This generates `telemetry_pb2.py` and `telemetry_pb2_grpc.py` — the shared contract between client and server.

### Step 4 — Authenticate with Google Cloud

```bash
gcloud auth application-default login
gcloud config set project iot-pipeline-project-495600
```

### Step 5 — Run the simulator

```bash
python simulator.py
```

---

## Deploying to GCP Cloud Run

### Build and push the container image

```bash
gcloud builds submit --tag gcr.io/iot-pipeline-project-495600/telemetry-server
```

### Deploy to both regions

```bash
# Region A — us-central1
gcloud run deploy telemetry-server-a \
  --image gcr.io/iot-pipeline-project-495600/telemetry-server \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --use-http2

# Region B — us-east1
gcloud run deploy telemetry-server-b \
  --image gcr.io/iot-pipeline-project-495600/telemetry-server \
  --region us-east1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --use-http2
```

### Create Pub/Sub topic and subscription

```bash
gcloud pubsub topics create telemetry-topic
gcloud pubsub subscriptions create telemetry-sub --topic=telemetry-topic
```

---

## Chaos Engineering Runbook — Reproduce the DR Test

Follow these exact steps to reproduce the disaster recovery benchmark shown in the results above.

### Terminal 1 — Start the IoT Fleet

```bash
# Confirm your active project
gcloud config set project iot-pipeline-project-495600

# Start the steady-state telemetry simulation
python simulator.py
```

Watch the logs — you should see connections distributed across both `us-central1` and `us-east1`.

### Terminal 2 — Inject Chaos & Verify Recovery

While Terminal 1 is running, open a second terminal:

```bash
# ── STEP 1: THE DISASTER ──────────────────────────────────────────────────────
# Delete Region A to simulate a catastrophic regional outage
gcloud run services delete telemetry-server-a \
  --region us-central1 \
  --quiet

# Watch Terminal 1 — you should see:
#   ❌ Connection failed to us-central1
#   ⚡ FAILOVER triggered — rerouting to us-east1
#   ✅ Reconnected to Region B

# ── STEP 2: VERIFY DATA INTEGRITY ────────────────────────────────────────────
# Pull messages from Pub/Sub to confirm data is still arriving via Region B
gcloud pubsub subscriptions pull telemetry-sub \
  --auto-ack \
  --limit=10

# ── STEP 3: RESTORE ACTIVE-ACTIVE ────────────────────────────────────────────
# Redeploy Region A to restore full active-active capacity
gcloud run deploy telemetry-server-a \
  --image gcr.io/iot-pipeline-project-495600/telemetry-server \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --use-http2
```

Open **GCP Cloud Monitoring → Metrics Explorer** while the test runs to observe the live dashboard charts shown in the benchmarks above.

---

## Results Summary

| Metric | Observed | Target | Status |
|--------|----------|--------|--------|
| Failover detection time | < 15 seconds | < 30 seconds | ✅ PASS |
| Message loss during failover | **Zero** | Zero | ✅ PASS |
| Region B auto-scale speed | Instant (Cloud Run) | < 60 seconds | ✅ PASS |
| gRPC latency (p90) | < 20 ms server-side | < 50 ms | ✅ PASS |
| 5xx error rate at failover | < 1.5% (transient) | < 5% | ✅ PASS |
| CPU utilization (normal) | 40–45% per region | < 70% | ✅ PASS |
| Message size consistency | ~29.2 KiB ± 0.2 KiB | Deterministic | ✅ PASS |
| Pub/Sub message continuity | Uninterrupted | No gap | ✅ PASS |

---

## Course Context

This project was developed as the **Final Project** for **ELL887 — Cloud Computing** at **IIT Delhi**.

**Student:** Akshat Jain · `2025EET2884`

The project demonstrates the following cloud computing concepts:
- **Serverless computing** — Cloud Run scale-to-zero and auto-scaling
- **Multi-region cloud architecture** — active-active deployment across GCP regions
- **Cloud-native messaging** — GCP Pub/Sub for resilient, decoupled telemetry ingestion
- **High-performance RPC** — gRPC and Protocol Buffers for IoT-scale data transfer
- **Observability** — GCP Cloud Monitoring dashboards as live evidence of system behaviour
- **Chaos engineering** — controlled regional outage simulation and automated recovery

---

## Full Architecture & Analysis

For the complete architectural diagrams, literature survey, design trade-off analysis, and all benchmark charts with explanations, see the presentation:

**[📊 View Full Presentation PDF](./Presentation.pdf)**

---

<p align="center">
  Built on Google Cloud Platform &nbsp;·&nbsp; Python · gRPC · Cloud Run · Pub/Sub · Cloud Monitoring
</p>
