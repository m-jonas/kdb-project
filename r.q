/ r.q - Real-time Database script

/ 1. Define the update function
/ The TP calls this remotely: upd[tableName; tableData]
upd:insert;

/ 2. Connect and Subscribe to the Tickerplant
/ Replace 5010 with your TP port. 
/ .u.sub[tableName; symbolList] -> ` is wildcard for "all"
h:hopen `:localhost:5010;
h"(.u.sub[`;`])";

/ 3. Success Message
-1 "RDB connected to TP on port 5010 and subscribed to all symbols.";