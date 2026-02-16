# Real-Time Crypto Analytics Engine (KDB+/q)

![KDB+](https://img.shields.io/badge/KDB%2B-5.0-blue) ![Python](https://img.shields.io/badge/Python-3.10-yellow) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

## 📊 Dashboard Preview
![Real-Time Dashboard](images/dashboard.png)
*Live Streamlit dashboard visualizing 1-minute OHLC bars and VWAP from KDB+ CEP engine.*

## 📖 Project Overview
This project is a high-frequency trading (HFT) data pipeline built with **KDB+/q** and **Python**. It mimics an institutional "Tick Architecture" to capture live cryptocurrency market data, persist it to a historical database (HDB), and calculate real-time analytics with microsecond latency.

**Key Capabilities:**
* **Ingestion:** Normalizes WebSocket feeds (Coinbase) into KDB+ IPC updates.
* **Analytics:** Real-time Vectorized VWAP and Order Book Imbalance calculation.
* **Aggregation:** Automatic generation of 1-minute OHLCV bars.
* **Persistence:** End-of-Day (EOD) logic to flush in-memory data to on-disk HDB partitions.
* **Ops:** Fully containerized microservices architecture using Docker Compose.

## 🏗️ Architecture
The system follows a standard **kdb+tick** architecture, decoupled into microservices:

```mermaid
graph TD
    A[Coinbase WebSocket] -->|JSON| B(Python Feed Handler)
    B -->|IPC Async| C{Tickerplant :5010}
    C -->|Upd| D[RDB :5011]
    C -->|Upd| E[CEP Engine :5012]
    D -->|End of Day| F[(HDB Disk)]
    E -->|Query| G[Streamlit Dashboard]