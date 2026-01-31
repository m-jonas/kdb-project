# Real-Time Crypto Analytics Engine (KDB+/q)

## Project Overview
This project is a high-frequency trading (HFT) data pipeline built with **KDB+/q** and **Python**. It captures live Level 1 market data from Coinbase, persists it to a historical database (HDB), and calculates real-time analytics (VWAP, Order Book Imbalance, and OHLC bars) with microsecond latency.

## Architecture
**Data Flow:** `Coinbase WebSocket` -> `Python Feedhandler` -> `Tickerplant (TP)` -> `RDB` & `CEP Engine`

* **Feed Handler:** Python `pykx` script normalizing JSON to kdb+ IPC.
* **Tickerplant:** Zero-latency router (Vanilla Tick).
* **RDB:** In-memory database for real-time queries.
* **CEP Engine:** Complex Event Processor calculating live VWAP and 1-minute OHLC bars.
* **HDB:** On-disk historical database partitioned by date.

## Key Features
* **Live Analytics:** Real-time calculation of Volume Weighted Average Price (VWAP) and Order Book Imbalance.
* **Time-Series Aggregation:** Automatic generation of 1-minute OHLCV bars from raw ticks.
* **Data Persistence:** End-of-Day (EOD) logic to flush RDB to HDB and manage partitions.
* **Resilience:** Reconnection logic and data integrity checks.

## Quick Start
1.  **Start Tickerplant:** `q tick.q sym . -p 5010`
2.  **Start RDB:** `q r.q -p 5011`
3.  **Start CEP Engine:** `q cep.q -p 5012`
4.  **Start Feed:** `python cb_feedhandler.py`
5.  **Perform EOD:** `.u.end[.z.D]`

## Tech Stack
* **Core:** KDB-X 5.0 (Community Edition), Q Language
* **Integration:** Python 3.12, PyKX, Websockets
* **Ops:** WSL, Bash