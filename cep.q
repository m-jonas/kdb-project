/ cep.q - Real-Time Analytics & OHLC Engine

/ 1. Configuration
ONE_MIN:0D00:01;

/ 2. Define Schemas
vwapState:([sym:`symbol$()] 
    totalVol:`float$(); 
    totalVal:`float$()
 );

/ OHLC Bar Table (Persisted in Memory)
ohlc:([time:`timespan$(); sym:`symbol$()] 
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
        / A. Real-Time VWAP
        vwapState+::([sym:x`sym] 
            totalVol:x`size; 
            totalVal:x[`price]*x`size
        );

        / B. Buffer for OHLC
        tradeBuffer,::select time, sym, price, size from x;
    ];
 };

/ 5. Real-Time Bar Generation (Timer Based)
.z.ts:{
    cutoff:ONE_MIN xbar .z.N;
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
        
        / Persist to global table
        `ohlc upsert bars;
        
        -1 ">>> OHLC Bar Published: ", string .z.T;
        
        / Clean buffer
        delete from `tradeBuffer where time < cutoff;
    ];
 };

/ 6. Connect
if[not system"p"; system"p 5012"];
h:@[hopen; `:localhost:5010; {0}];
if[h>0; h"(.u.sub[`ticker;`])"; -1 "CEP Connected."];

/ 7. Start Timer
\t 1000