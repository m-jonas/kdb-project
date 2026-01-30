/ r.q - Real-time Database script with EOD Persistence

/ 1. Configuration
/ Define the path to your historical database root
hdbroot:hsym `$getenv[`HDB_PATH] / Use env var or hardcode like `:./hdb
if[null hdbroot; hdbroot:`$":./hdb"];

/ 2. Define the update function
/ The TP calls this remotely via pykx or other feedhandlers: upd[tableName; tableData]
/ In your current setup, ticker is the main table [cite: 86]
upd:insert;

/ 3. Define the End-of-Day (.u.end) function
/ This is triggered by the Tickerplant when the date changes [cite: 79, 80]
.u.end:{[d]
  / Get all tables currently in the root namespace
  t:tables`.;
  
  / Filter for tables that contain data (checking for 'sym' column)
  t:t where `sym in/:cols each t;
  
  / Loop through each table to save to the HDB
  {[d;x]
    / Generate the path for the specific date partition (e.g., :hdb/2025.10.21/ticker/)
    targetpath:.Q.par[hdbroot;d;x];
    
    / Enumerate symbols against the sym file and save to disk
    / .Q.en ensures the HDB remains performant by using symbol pointers
    targetpath set .Q.en[hdbroot] value x;
    
    / Clear the local table in RDB memory to start fresh for the new day
    @[`.;x;0#];
    
    -1 "Successfully persisted table '", (string x), "' to HDB for date ", string d;
  }[d] each t;
  
  / Force garbage collection to release memory back to the OS
  .Q.gc[];
  
  -1 "EOD processing complete.";
 };

/ 4. Connect and Subscribe to the Tickerplant
/ Defaulting to port 5010 as defined in your tick.q [cite: 78, 85]
tp_port:5010;
h:@[hopen; `:localhost:5010; {short_err: "Failed to connect to TP on 5010: ", x; -2 short_err; 0}];

if[h > 0;
    / .u.sub[tableName; symbolList] -> ` is wildcard for "all" [cite: 74, 75]
    h"(.u.sub[`;`])";
    -1 "RDB connected to TP on port 5010 and subscribed to all symbols.";
 ];

/ 5. Error Handling & Logging
if[h = 0; -1 "Warning: RDB starting in standalone mode. Connect to TP manually using h:hopen `:localhost:5010"];