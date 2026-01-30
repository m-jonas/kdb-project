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
/ Result: Range from -1 (Strong Sell Pressure) to +1 (Strong Buy Pressure)
calcImbalance:{[bidSize; askSize]
    (bidSize - askSize) % (bidSize + askSize)
 };

/ 3. Define the Update Function (.u.upd)
/ This function is called automatically by the Tickerplant for every new batch of data
upd:{[t;x]
    / Only process the 'ticker' table
    if[t~`ticker;
        
        / A. Update Running VWAP State
        / We use "upsert" to update the running totals for the incoming symbols
        / x[1] is symbol, x[2] is price, x[3] is size
        vwapState+::([sym:x 1] 
            totalVol:x 3; 
            totalVal:x[2]*x 3
        );

        / B. Calculate Snapshot Analytics
        / We create a temporary table with the new analytics
        analytics:([]
            time:.z.T;
            sym:x 1;
            price:x 2;
            vwap:vwapState[x 1; `totalVal] % vwapState[x 1; `totalVol];
            imbalance:calcImbalance[x 6; x 7] / x[6] is bidSize, x[7] is askSize
        );

        / C. Display or Publish
        / For now, we just print to console to prove it works
        show analytics;
        
        / In a real system, you would publish this back to the TP:
        / .u.pub[`analytics; analytics];
    ];
 };

/ 4. Connect to Tickerplant
/ Default port 5010
if not system"p"; system"p 5012]; / CEP runs on port 5012

h:@[hopen; `:localhost:5010; {0}];
if[h>0;
    h"(.u.sub[`ticker;`])";
    -1 "CEP Engine connected to TP and calculating Analytics...";
 ];

if[h=0; -1 "Waiting for TP... (Run 'hopen 5010' manually if needed)"];