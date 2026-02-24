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
/ Use .z.N (Timespan) to match 'tradeBuffer' schema in cep.q
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

/ 5. Test: Batch Update with Duplicate Symbols
/ Scenario: Batch update with 2 trades for same symbol.
/ Trade C: Price 100, Size 10
/ Trade D: Price 100, Size 10
/ Total Val: 2000, Total Vol: 20
/ Should not crash with duplicate key error.

mockBatch:{[p; s]
  ([] time:2#.z.N; sym:2#`BATCH_TEST; price:2#p; size:2#s;
      bid:2#0f; ask:2#0f; bidSize:2#0f; askSize:2#0f)
 };

/ Inject Batch
/ This will fail with 'dup key' without the fix in cep.q
@[{upd[`ticker; x]; -1 "[PASS] Batch Update (No Crash)"}; mockBatch[100f; 10f]; {-1 "[FAIL] Batch Update Crashed: ",x}];

/ Check Result if it didn't crash
r:select totalVal, totalVol from vwapState where sym=`BATCH_TEST;
if[count r;
    currVWAP:first[r`totalVal] % first[r`totalVol];
    if[currVWAP = 100f; -1 "[PASS] Batch VWAP Logic Correct (100.0)"];
    if[not currVWAP = 100f; -1 "[FAIL] Batch VWAP Logic. Expected 100.0, got ",string currVWAP];
 ];

-1 ">>> TESTS COMPLETE <<<";
exit 0;