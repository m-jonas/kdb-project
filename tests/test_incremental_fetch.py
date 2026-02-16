
import time
import pandas as pd
import numpy as np
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

class MockQResult:
    def __init__(self, df):
        self._df = df

    def pd(self):
        return self._df.copy()

class MockQConnection:
    def __init__(self):
        # Create a large initial DataFrame
        self.data = pd.DataFrame({
            'time': pd.to_timedelta(np.arange(100000), unit='s'),
            'sym': ['BTC'] * 100000,
            'open': np.random.rand(100000),
            'high': np.random.rand(100000),
            'low': np.random.rand(100000),
            'close': np.random.rand(100000),
            'volume': np.random.rand(100000),
            'vwap': np.random.rand(100000)
        })
        self.query_count = 0
        self.rows_fetched = 0

    def __call__(self, query, *args):
        # Simulate network latency
        time.sleep(0.01)
        self.query_count += 1

        if query == "0!ohlc":
            # Full table scan
            self.rows_fetched += len(self.data)
            return MockQResult(self.data)

        # Check for parametrized query
        # Mocking: q('0!select from ohlc where time > x', last_time)
        if "select from ohlc where time >" in str(query):
            if args:
                last_time = args[0]
                # Filter data
                delta = self.data[self.data['time'] > last_time]
                self.rows_fetched += len(delta)
                return MockQResult(delta)
            else:
                 # Try to parse string if args not provided (simplified)
                 return MockQResult(pd.DataFrame())

        return MockQResult(pd.DataFrame())

    def add_data(self, num_rows=1):
        last_time = self.data['time'].max()
        new_rows = pd.DataFrame({
            'time': [last_time + pd.Timedelta(seconds=1)] * num_rows,
            'sym': ['BTC'] * num_rows,
            'open': np.random.rand(num_rows),
            'high': np.random.rand(num_rows),
            'low': np.random.rand(num_rows),
            'close': np.random.rand(num_rows),
            'volume': np.random.rand(num_rows),
            'vwap': np.random.rand(num_rows)
        })
        self.data = pd.concat([self.data, new_rows], ignore_index=True)

# Optimized fetch function simulation
def fetch_data_optimized(q, state):
    if 'ohlc_data' not in state or state['ohlc_data'].empty:
        # Initial fetch
        res = q("0!ohlc")
        df = res.pd()
        state['ohlc_data'] = df
        return df

    # Delta fetch
    last_time = state['ohlc_data']['time'].max()

    # In real code: q('...', last_time)
    # Here we mock it
    res = q('0!select from ohlc where time > x', last_time)
    new_data = res.pd()

    if not new_data.empty:
        state['ohlc_data'] = pd.concat([state['ohlc_data'], new_data], ignore_index=True)

    return state['ohlc_data']

def run_benchmark_optimized():
    q = MockQConnection()
    state = {} # mimic st.session_state

    print("--- Benchmarking Optimized Implementation ---")
    start_total = time.time()

    # Initial load (will be full scan)
    fetch_data_optimized(q, state)

    # Simulate 5 iterations
    for i in range(5):
        # 1. Simulate data growth
        q.add_data(1)

        # 2. Fetch Data (Optimized: Delta)
        start_fetch = time.time()
        df = fetch_data_optimized(q, state)
        end_fetch = time.time()

        print(f"Iter {i+1}: Fetched (Total DF size: {len(df)}) in {end_fetch - start_fetch:.4f}s")

    end_total = time.time()
    print(f"Total Time: {end_total - start_total:.4f}s")
    print(f"Total Rows Transferred over Network: {q.rows_fetched}")
    return end_total - start_total, q.rows_fetched

if __name__ == "__main__":
    run_benchmark_optimized()
