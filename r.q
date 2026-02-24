/ r.q - Real-time Database script

/ 1. Configuration: Define where the HDB lives
/ Check if env var is set and not empty; otherwise default to :./hdb
envPath:getenv[`HDB_PATH];
hdbroot:$[count envPath; hsym `$envPath; `:./hdb];

/ Print it so you can verify in the console
-1 "HDB Root set to: ",string hdbroot;

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

tpHost:getenv[`TP_HOST];
/ Default to localhost:5010 if env var is missing
tpConnect:$[count tpHost; hsym `$(tpHost,":5010"); `:localhost:5010];

-1 ">>> RDB waiting for Tickerplant to bind port at ",string tpConnect;

h:0;
/ Loop infinitely until the connection succeeds
while[h=0;
    h:@[hopen; tpConnect; {0}];
    if[h=0; 
        system "sleep 1"; / Pause for 1 second before retrying
    ];
 ];

-1 ">>> RDB Connected! Subscribing to tables...";

/ Request the table schemas from the Tickerplant
tables_and_schemas: h"(.u.sub[`;`])";

/ If we received schemas, create them in the RDB's local memory
if[count tables_and_schemas;
    {(.[;();:;].)each x} tables_and_schemas;
 ];

-1 ">>> RDB Initialization Complete. Subscribed to all symbols.";