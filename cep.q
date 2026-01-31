/ cep.q - Real-Time Analytics & OHLC Engine

/ 1. Configuration
/ Define 1-minute timespan constant for readability
ONE_MIN:0D00:01;

/ 2. Define Schemas
vwapState:([sym:`symbol$()] 
    totalVol:`float$(); 
    totalVal:`float$()
 );

ohlc:([] 
    time:`timestamp$(); 
    sym:`symbol$(); 
    open:`float$(); 
    high:`float$(); 
    low:`float$(); 
    close:`float$(); 
    volume:`float$();
    vwap:`float$()
 );

/ Buffer matches the specific columns we need from the ticker
tradeBuffer:([] time:`timespan$(); sym:`symbol$(); price:`float$(); size:`float$());

/ 3. Helper Functions
calcImbalance:{[bidSize; askSize] (bidSize-askSize)%(bidSize+askSize)};

/ 4. The Update Function (.u.upd)
upd:{[t;x]
    if[t~`ticker;
        
        / --- Part A: Real-Time VWAP (Stateful) ---
        vwapState+::([sym:x`sym] 
            totalVol:x`size; 
            totalVal:x[`price]*x`size
        );

        / --- Part B: Snapshot Analytics ---
        / We retrieve the updated state to calculate the new VWAP
        currentVals:vwapState[x`sym];
        
        analytics:([]
            time:.z.T;
            sym:x`sym;
            price:x`price;
            / Safe vectorized lookup
            vwap:currentVals[`totalVal] % currentVals[`totalVol];
            imbalance:calcImbalance[x`bidSize;x`askSize]
        );
        / show analytics; 

        / --- Part C: OHLC Aggregation (Buffering) ---
        / Append only the relevant columns to the buffer
        tradeBuffer,::select time, sym, price, size from x;
    ];
 };

/ 5. Real-Time Bar Generation (Timer Based)
.z.ts:{
    / Use ONE_MIN constant and .z.N (timespan) for accurate masking
    cutoff:ONE_MIN xbar .z.N;
    
    / Select completed trades (older than the current minute bucket)
    completed:select from tradeBuffer where time < cutoff;
    
    if[count completed;
        / Calculate OHLC bars
        bars:select 
            open:first price, 
            high:max price, 
            low:min price, 
            close:last price, 
            volume:sum size,
            vwap:(sum price*size) % sum size
            by time:(ONE_MIN xbar time), sym 
            from completed;
        
        -1 ">>> NEW OHLC BAR GENERATED <<<";
        show bars;
        
        / Clean up the buffer
        delete from `tradeBuffer where time < cutoff;
    ];
 };

/ 6. Connect
if[not system"p"; system"p 5012"];
h:@[hopen; `:localhost:5010; {0}];
if[h>0; h"(.u.sub[`ticker;`])"; -1 "CEP Connected."];

/ 7. Start Timer (Check every 5 seconds)
\t 5000