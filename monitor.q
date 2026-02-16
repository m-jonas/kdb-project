/ monitor.q - Production Prometheus Exporter

/ 1. Force text/plain for `txt
.h.ty[`txt]:"text/plain";

/ 2. Initialize Message Counter
if[not `msgs in key `.mon; .mon.msgs:0];

/ 3. Create a "Hook" into the Update Function (.u.upd)
/ This wraps the original function to count every update before processing it
if[not `upd_orig in key `.u; 
    .u.upd_orig:.u.upd;
    .u.upd:{[t;x] 
        .mon.msgs+:1;       / Increment counter
        .u.upd_orig[t;x]    / Call original function
    }
 ];

.z.ph:{[x]
  url:first x;

  / Universal Match
  if[not any url like/:("/metrics*"; "metrics*"); 
      :.h.hy[`html; "Go to /metrics. You requested: ",url]
  ];

  / --- Gather Stats ---
  w:.Q.w[];
  metrics:();
  
  metrics,:enlist "kdb_mem_used_bytes ",string `int$w`used;
  metrics,:enlist "kdb_mem_heap_bytes ",string `int$w`heap;
  metrics,:enlist "kdb_global_vars ",string count key `.q;
  metrics,:enlist "kdb_client_count ",string count key .z.W;
  metrics,:enlist "kdb_msg_count ",string .mon.msgs;
  
  / --- Safe Table Counts (Will be 0 on TP, High on RDB) ---
  rows:0;
  if[`ticker in tables[]; rows:count value `ticker];
  metrics,:enlist "kdb_table_rows{table=\"ticker\"} ",string rows;
  
  / --- Safe Symbol Count ---
  syms:0;
  if[`sym in key `.; syms:count value `sym];
  metrics,:enlist "kdb_sym_count ",string syms;

  / --- Response ---
  txt:"\n" sv metrics;
  .h.hy[`txt; txt]
 };

-1 ">>> Prometheus Exporter loaded (Silent Mode + Msg Counter).";