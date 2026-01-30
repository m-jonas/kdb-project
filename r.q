/ r.q - Real-time Database script

/ 1. Configuration: Define where the HDB lives
/ Tries to read $HDB_PATH. If empty, defaults to a local folder named "hdb"
hdbroot:hsym `$getenv[`HDB_PATH];
if[hdbroot~`:; hdbroot:`$":./hdb"];

/ 2. Define the update function
/ The TP calls this remotely: upd[tableName; tableData]
upd:insert;

/ 3. Define the End-of-Day (.u.end) function
/ This is the function causing your error - it was missing!
.u.end:{[d]
  -1 "Starting EOD for ",string d;
  
  / Filter for tables that have a 'sym' column (data tables)
  t:tables`.;
  t:t where `sym in/:cols each t;
  
  / Save each table to the HDB
  {[d;x]
    / Construct path: ./hdb/2026.01.30/ticker/
    targetpath:.Q.par[hdbroot;d;x];
    
    / Save to disk (enumerate against sym file)
    / This converts symbols to integers for performance
    targetpath set .Q.en[hdbroot] value x;
    
    / Clear memory in RDB so we start fresh
    @[`.;x;0#];
    
    -1 "Saved and cleared ",(string x);
  }[d] each t;
  
  / Garbage Collect to free RAM
  .Q.gc[];
  -1 "EOD Complete.";
 };

/ 4. Connect and Subscribe to the Tickerplant
/ Defaulting to port 5010 
/ We check if connection exists before subscribing
if[not system"p"; system"p 5011"]; / RDB listens on 5011

h:@[hopen; `:localhost:5010; {0}];
if[h>0; 
  h"(.u.sub[`;`])"; 
  -1 "RDB connected to TP on port 5010 and subscribed to all symbols.";
 ];

if[h=0; -1 "Warning: Could not connect to TP. RDB is in standalone mode."];