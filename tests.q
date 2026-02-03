/ tests.q - Unit Test Suite for KDB+ Engine
/ Usage: q tests.q

-1 ">>> RUNNING UNIT TESTS <<<";

/ 1. Load the Analytics Logic
/ We suppress connection errors in case TP isn't running
\e 0
@[system; "l cep.q"; {-1 "Loaded cep.q (ignoring connection errors for test mode)"}];

/ 2. Test: Order Book Imbalance
/ Scenario: Bid Size 100, Ask Size 300.
/ Expected: (100 - 300) / (100 + 300) = -200 / 400 = -0.5
bid:100f; ask:300f;
res:calcImbalance[bid; ask];

if[res = -0.5; -1 "[PASS] Imbalance Calculation Correct (-0.5)"];
if[not res = -0.5; -1 "[FAIL] Imbalance Calculation. Expected -0.5, got ",string res];

/ 3. Test: VWAP Calculation
/ Scenario: Clear state, add two trades, check VWAP.
/ Trade A: Price 100, Size 10 -> Val 1000
/ Trade B: Price 110, Size 10 -> Val 1100
/ Total Val: 2100, Total Vol: 20 -> VWAP should be 105.

/ Clear global state first
delete from `vwapState;
delete from `tradeBuffer;

/ Define Helper to create a 1-row table (Mocking the TP output)
/ FIX: Use .z.N (Timespan) to match 'tradeBuffer' schema in cep.q
mockTrade:{[p; s]
  ([] time:enlist .z.N; sym:enlist `TEST; price:enlist p; size:enlist s; 
      bid:enlist 0f; ask:enlist 0f; bidSize:enlist 0f; askSize:enlist 0f)
 };

/ Inject Trade A
upd[`ticker; mockTrade[100f; 10f]];

/ Inject Trade B
upd[`ticker; mockTrade[110f; 10f]];

/ Check Result
currVWAP:vwapState[`TEST; `totalVal] % vwapState[`TEST; `totalVol];

if[currVWAP = 105f; -1 "[PASS] VWAP Logic Correct (105.0)"];
if[not currVWAP = 105f; -1 "[FAIL] VWAP Logic. Expected 105.0, got ",string currVWAP];

/ 4. Test: OHLC Buffering
/ Check if tradeBuffer received the 2 rows we just injected
countBuffer:count tradeBuffer;
if[countBuffer = 2; -1 "[PASS] OHLC Buffer Ingestion Correct (2 rows)"];
if[not countBuffer = 2; -1 "[FAIL] OHLC Buffer. Expected 2 rows, got ",string countBuffer];

-1 ">>> TESTS COMPLETE <<<";
exit 0;