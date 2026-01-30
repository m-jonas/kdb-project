/ r.q - Real-time Database script with Logging and EOD Persistence

/ 1. Configuration
/ Define the path to your historical database root
hdbroot:hsym `$getenv[`HDB_PATH]
if[null hdbroot; hdbroot:`$":./hdb"];

/ 2. Logging Function
/ Prepends a nanosecond timestamp and writes to both stdout and a file
log:{[msg] 
  msg:(string .z.P)," ",msg; 
  -1 msg; / Write to terminal (stdout)
  h:@[hopen; `:rdb_activity.log; {0}]; 
  if[h>0; h msg,"\n"; hclose h];
 };

/ 3. Define the update function
/ The TP calls this remotely: upd[tableName; tableData] 
upd:insert;

/ 4. End-of-Day (.u.end) function
/ Triggered by Tickerplant to persist data to HDB
.u.end:{[d]
  log "Starting EOD for date: ",string d;
  t:tables`.;
  t:t where `sym in/:cols each t;
  
  {[d;x]
    targetpath:.Q.par[hdbroot;d;x];
    targetpath set .Q.en[hdbroot] value x;
    @[`.;x;0#]; / Clear memory for new day
    log "Persisted table '", (string x), "' to HDB.";
  }[d] each t;
  
  .Q.gc[]; / Garbage collection
  log "EOD processing complete.";
 };

/ 5. Connect and Subscribe to the Tickerplant [cite: 85]
tp_port:5010;
h:@[hopen; `:localhost:5010; {log "Failed to connect to TP: ", x; 0}];

if[h > 0;
    / Subscribe to all tables and all symbols [cite: 86]
    h"(.u.sub[`;`])";
    log "RDB connected to TP on port 5010 and subscribed to all symbols.";
 ];

if[h = 0; log "Warning: RDB starting in standalone mode."];