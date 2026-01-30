/ cep.q - Real-Time Complex Event Processing Engine

/ 1. Define State
/ We keep a keyed table to store the running state for each symbol
vwapState:([sym:`symbol$()] 
    totalVol:`float$(); 
    totalVal:`float$()
 );

/ 2. Define Analytics Functions

/ Calculate Order Book Imbalance
/ Formula: (BidSize - AskSize) / (BidSize + AskSize)
calcImbalance:{[bidSize; askSize]
    (bidSize - askSize) % (bidSize + askSize)
 };

/ 3. Define the Update Function (.u.upd)
upd:{[t;x]
    if[t~`ticker;
        
        / x is a Table, so we access columns by Name (`sym, `price, `size)
        
        / A. Update Running VWAP State
        vwapState+::([sym:x`sym] 
            totalVol:x`size; 
            totalVal:x[`price] * x`size
        );

        / B. Calculate Snapshot Analytics
        analytics:([]
            time:.z.T;
            sym:x`sym;
            price:x`price;
            vwap:vwapState[x`sym; `totalVal] % vwapState[x`sym; `totalVol];
            imbalance:calcImbalance[x`bidSize; x`askSize] 
        );

        / C. Display 
        show analytics;
        
        / D. Publish (Optional)
        / .u.pub[`analytics; analytics];
    ];
 };

/ 4. Connect to Tickerplant
/ Default port 5010
/ CEP runs on port 5012
if[not system"p"; system"p 5012"];

h:@[hopen; `:localhost:5010; {0}];
if[h>0;
    h"(.u.sub[`ticker;`])";
    -1 "CEP Engine connected to TP and calculating Analytics...";
 ];

if[h=0; -1 "Waiting for TP... (Run 'hopen 5010' manually if needed)"];