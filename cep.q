/ cep.q - Complex Event Processor
/ Real-Time Analytics & OHLC Engine Logic

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
    vwap:`float$();
    imbalance:`float$()
 );

/ Buffer matches the specific columns we need from the ticker
tradeBuffer:([] time:`timespan$(); sym:`symbol$(); price:`float$(); size:`float$(); bidSize:`float$(); askSize:`float$());

/ 3. Helper Functions
calcImbalance:{[bidSize;askSize] (bidSize-askSize)%(bidSize+askSize)};

/ 4. The Update Function (.u.upd)
upd:{[t;x]
    / --- LIVE CRYPTO ANALYTICS & TRADING ---
    if[t~`ticker;
        / A. Real-Time VWAP
        agg:select totalVol:sum size, totalVal:sum price*size by sym from x;
        vwapState+::agg;

        / B. Buffer for OHLC
        tradeBuffer,::select time, sym, price, size, bidSize, askSize from x;

        / C. ALGO SIGNAL GENERATOR (Tight Spread)
        tight_spreads: select from x where (ask - bid) <= 0.50;
        
        if[count tight_spreads;
            new_signals: select time:.z.n, sym:sym, side:`BUY, qty:1j, price:ask from tight_spreads;
            h(`.u.upd; `signals; value flip new_signals);
            -1 "!!! TIGHT SPREAD DETECTED: Firing BUY signal for ", string[count new_signals], " BTC !!!";
        ];
    ];
 };

/ 5. Real-Time Bar Generation (Timer Based)
.z.ts:{
    cutoff:ONE_MIN xbar .z.N;
    completed:select from tradeBuffer where time < cutoff;
    
    if[count completed;
        / Calculate OHLC bars and Imbalance
        bars:select 
            open:first price, 
            high:max price, 
            low:min price, 
            close:last price, 
            volume:sum size,
            vwap:(sum price*size) % sum size,
            imbalance:last calcImbalance[bidSize;askSize]
            by time:(ONE_MIN xbar time), sym 
            from completed;
            
        / Persist to global table using upsert (safely maps columns by name)
        `ohlc upsert bars;
        
        -1 ">>> OHLC Bar Published: ", string .z.T;
        
        / Clean buffer
        tradeBuffer::delete from tradeBuffer where time < cutoff;
    ];
 };

/ 6. Connect
if[not system"p"; system"p 5012"];
tpHost:getenv[`TP_HOST];
tpConnect:$[count tpHost; hsym `$(tpHost,":5010"); `:localhost:5010];
-1 "Connecting to TP at ",string tpConnect;
h:@[hopen; tpConnect; {0}];
if[h>0; h"(.u.sub[`ticker;`])"; -1 "CEP Connected."];

/ 7. Start Timer
\t 1000