# F1 Telemetry & Analytics API Engine

A high-performance, asynchronous backend API built with FastAPI designed to ingest, clean, and cache live Formula 1 track telemetry data. This project showcases production-ready backend design patterns including in-memory caching strategies, third-party API orchestration, data normalization, and system performance optimization.

## 🚀 Key Features
- **Live Ingestion Infrastructure**: Integrates with the open-source OpenF1 API to capture vehicle dynamics sampled at ~3.7 Hz.
- **Performance Caching Layer**: Implements an in-memory caching mechanism with Time-To-Live (TTL) expiration to bypass upstream network bottlenecks and prevent API throttling.
- **Self-Documenting REST API**: Utilizes FastAPI and Pydantic for automated OpenAPI specification mapping and real-time parameter validation.

## 🛠️ System Architecture



- **FastAPI / Uvicorn**: High-concurrency ASGI web framework handling asynchronous data routing.
- **In-Memory Store**: Tracks cache state and invalidation logic to reduce system response times to under 2ms.
- **Telemetry Processing Module**: Slices, reverses, and normalizes high-frequency raw arrays into optimized payloads.

## 📦 Tech Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Server**: Uvicorn
- **Environment Management**: Python venv (Isolated)

## 🔧 Installation & Local Setup

### 1. Prerequisites
Ensure you have the Python 3 launcher (`py`) installed on your Windows machine.

### 2. Initialize Environment & Install Dependencies
```powershell
# Clone the repository
git clone [https://github.com/sahasan95/f1-telemetry-api.git](https://github.com/sahasan95/f1-telemetry-api.git)
cd f1-telemetry-api

# Create and activate virtual environment
py -m venv .venv
# (Ensure your IDE/Terminal activates the workspace environment)

# Install locked dependencies
pip install -r requirements.txt