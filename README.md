# Real-Time Market Data & Trading Engine (KDB+ / ITCH / Crypto)

![KDB+](https://img.shields.io/badge/KDB%2B-5.0-blue) ![Python](https://img.shields.io/badge/Python-3.10-yellow) ![PyKX](https://img.shields.io/badge/PyKX-IPC-orange) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

## 📊 System Visualizations
| Crypto Real-Time Dashboard | Nasdaq L2 Depth of Market (Terminal) |
| :---: | :---: |
| ![Dashboard](images/dashboard.png) | ![ITCH DOM](images/Screenshot%202026-02-19%20204559.png) |
| *Live Streamlit dashboard visualizing 1-minute OHLC bars and VWAP from KDB+ CEP engine.* | *Terminal-based Level 2 Order Book built from raw binary ITCH 5.0 payloads.* |

## 📖 Project Overview
This project is a high-frequency trading (HFT) data pipeline built with **KDB+/q** and **Python**. It mimics an institutional "Tick Architecture" to process both unstructured WebSockets (Crypto) and raw binary network streams (Traditional Equities) into a centralized, high-performance database with microsecond latency.

**Key Technical Capabilities:**
* **Level 3 Binary Data Parsing:** Engineered a highly optimized Python feed handler to ingest, decode, and process raw Nasdaq TotalView-ITCH 5.0 payloads.
* **Limit Order Book (LOB) State Machine:** In-memory tracking of the complete lifecycle of millions of equity orders (Add, Execute, Cancel, Replace, Delete) in real-time.
* **Level 3 to Level 2 Aggregation:** Extracts actionable Best Bid and Offer (BBO) signals from the L3 firehose, highly compressing data before async publication to KDB+.
* **Historical Data ETL:** High-performance Python ETL pipeline to extract Level 2 BBO from historical ITCH binaries and bulk load natively partitioned data directly to disk via `.Q.dpft`.
* **Crypto Ingestion:** Normalizes WebSocket JSON feeds (Coinbase, Kraken) into kdb+ IPC updates.
* **Complex Event Processing (CEP):** Real-time Vectorized VWAP, Order Book Imbalance, and continuous OHLCV bar generation.
* **Persistence:** End-of-Day (EOD) logic to flush in-memory data to on-disk partitioned Historical Databases (HDB).
* **Ops & Observability:** Fully containerized microservices architecture with Prometheus and Grafana monitoring.

## 🏗️ Architecture Flow
The system follows a standard **kdb+tick** architecture, decoupled into microservices:

```mermaid
graph TD
    A[Coinbase/Kraken WebSockets] -->|JSON| B(Crypto Feed Handlers)
    I[Nasdaq ITCH 5.0 Binary] -->|Struct Unpack| J(L3 to L2 Python Engine)
    B -->|PyKX IPC| C{Tickerplant :5010}
    J -->|PyKX IPC Async| C
    C -->|Upd| D[RDB :5011]
    C -->|Upd| E[CEP Engine :5012]
    D -->|End of Day| F[(HDB Disk)]
    E -->|Query| G[Streamlit Dashboard]
```

## 🚀 Quick Start (Docker)
The easiest way to run the stack is via Docker Compose.

Prerequisites:

Docker Desktop installed.

A valid `kc.lic` (KDB+ License) placed in the root directory.

A `cdp_api_key.json` (Coinbase Credentials) in the root directory.

(Optional) Download the Nasdaq ITCH sample file and place it in a data/ directory.

1. Configure Environment
Create a .env file in the root directory to set your local hostname (required for KDB+ license validation).

```
cp .env.example .env
# Edit .env and set KDB_HOSTNAME to your machine's hostname (e.g., 'my-laptop')
```

2. Build & Run the KDB+ Stack

```
docker-compose build
docker-compose up -d
```

*Access the Crypto Dashboard at http://localhost:8501*

3. Start the Nasdaq ITCH Feed Handler

Once the Tickerplant is running, start the Python parser to stream Level 2 BBO updates into the KDB+ database:

```
python itch_parser_kdb.py
```

## 🛠️ Interacting with the Data

**Checking the RDB (Real-Time Database)**
You can connect directly to the in-memory database to query the live streams:

```
# Attach to the RDB container
docker exec -it kdb_rdb q -p 5011

# Inside the q terminal:
q) h:hopen 5011
q) h"count ticker"    / Check Crypto trades
q) h"count bbo"       / Check Nasdaq Level 2 updates
q) h"select top 10 from bbo"
```

**Historical Data ETL (Batch Processing)**
To bypass the Real-Time Tickerplant and bulk load historical data directly into the partitioned HDB:
```
python itch_hdb_etl.py
```
*This script parses the binary ITCH file, extracts the BBO, converts the data into pure KDB+ typed vectors, and natively saves it to disk via `.Q.dpft.`*

**Data Persistence (HDB)**
The system is designed to save data to disk automatically at midnight. To test this manually (Force EOD):
```
q) h:hopen 5011
q) h".u.end[.z.D]"
```
*This triggers the RDB to save in-memory tables to the hdb/ directory, partition them by date, and clear RAM.*

## ✅ Automated Testing
This project includes a regression test suite to verify the mathematical accuracy of the analytics engine (VWAP/Imbalance) before deployment.

Run Unit Tests:

`q tests.q`

Expected Output:

```
>>> RUNNING UNIT TESTS <<<
[PASS] Imbalance Calculation Correct (-0.5)
[PASS] VWAP Logic Correct (105.0)
[PASS] OHLC Buffer Ingestion Correct (2 rows)
```

## 📂 Project Structure

Infrastructure & Analytics (KDB+)

- `tick.q` - Master Tickerplant routing engine.

- `r.q` - Fault-tolerant Real-Time Database (RDB) with robust connection retry logic.

- `cep.q` - Complex Event Processing engine for VWAP and OHLC generation.

- `tick/sym.q` - Schema definitions for ticker (Crypto) and bbo (Equities) tables.

- `hdb/` - On-disk partitioned historical database.

Market Data Handlers (Python)

- `itch_parser_kdb.py` - Core L3 ITCH parser, L2 aggregator, and PyKX publisher.

- `itch_hdb_etl.py` - High-performance Historical ETL pipeline for bulk KDB+ HDB onboarding.

- `itch_parser_dash.py` - Terminal-based visual Depth of Market (DOM) ladder.

- `coinbase_feedhandler.py` - Async WebSocket ingestion for Coinbase.

- `kraken_feedhandler.py` - Async WebSocket ingestion for Kraken.

Ops & Visuals

- `dashboard.py` - Streamlit application querying the CEP engine.

- `docker-compose.yml` - Microservices orchestration.

- `prometheus.yml` / `monitor.q` - Infrastructure observability stack.