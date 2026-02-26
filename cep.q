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
    vwap:`float$()
 );

/ Buffer matches the specific columns we need from the ticker
tradeBuffer:([] time:`timespan$(); sym:`symbol$(); price:`float$(); size:`float$());

/ 3. Helper Functions
calcImbalance:{[bidSize; askSize] (bidSize-askSize)%(bidSize+askSize)};

/ 4. The Update Function (.u.upd)
upd:{[t;x]
    / --- LIVE CRYPTO ANALYTICS & TRADING ---
    if[t~`ticker;
        / A. Real-Time VWAP
        agg:select totalVol:sum size, totalVal:sum price*size by sym from x;
        vwapState+::agg;

        / B. Buffer for OHLC
        tradeBuffer,::select time, sym, price, size from x;

        / C. ALGO SIGNAL GENERATOR (Momentum Follower)
        / If we see a single trade with a size greater than 0.5 (e.g., half a Bitcoin), trigger a trade!
        whale_trades: select from x where size > 0.5;
        
        if[count whale_trades;
            / Construct the FIX-ready signal (We'll default to buying 1 unit)
            new_signals: select time:.z.n, sym:sym, side:`BUY, qty:1j, price:price from whale_trades;
            
            / Publish the signal back to the Tickerplant
            h(`.u.upd; `signals; value flip new_signals);
            
            -1 "!!! WHALE DETECTED: Firing momentum signal for ", string[count new_signals], " trade(s) !!!";
        ];
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
        
        / Clean buffer (Explicit global assignment to fix memory leak)
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