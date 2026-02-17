/ monitor.q - Syntax Safe Prometheus Exporter

/ 1. Force text/plain
.h.ty[`txt]:"text/plain";

/ 2. Init Counter
if[not `msgs in key `.mon; .mon.msgs:0];

/ --- 3. Define Helper Functions (Prevents Syntax Errors) ---

/ Helper to wrap Tickerplant function (.u.upd)
.mon.wrapTP:{
  if[`upd_orig in key `.u; :()]; / Exit if already wrapped
  .u.upd_orig:.u.upd;
  .u.upd:{[t;x] .mon.msgs+:1; .u.upd_orig[t;x]};
  -1 ">>> Monitor: Wrapped .u.upd (TP Mode)";
 };

/ Helper to wrap RDB function (global upd)
.mon.wrapRDB:{
  if[`upd_orig in key `.; :()]; / Exit if already wrapped
  .upd_orig:upd;
  upd:{[t;x] .mon.msgs+:1; .upd_orig[t;x]};
  -1 ">>> Monitor: Wrapped global upd (RDB Mode)";
 };

/ --- 4. Execution Logic ---

/ Check where we are running and call the appropriate helper
if[`upd in key `.u; .mon.wrapTP[]];
if[`upd in key `.; .mon.wrapRDB[]];

/ --- 5. HTTP Handler ---

.z.ph:{[x]
  url:first x;
  if[not any url like/:("/metrics*"; "metrics*"); 
      :.h.hy[`html; "Go to /metrics. You requested: ",url]
  ];

  / Gather Stats
  w:.Q.w[];
  metrics:();
  metrics,:enlist "kdb_mem_used_bytes ",string `int$w`used;
  metrics,:enlist "kdb_mem_heap_bytes ",string `int$w`heap;
  metrics,:enlist "kdb_global_vars ",string count key `.q;
  metrics,:enlist "kdb_client_count ",string count key .z.W;
  metrics,:enlist "kdb_msg_count ",string .mon.msgs;
  
  / Safe Table Counts
  rows:0;
  if[`ticker in tables[]; rows:count value `ticker];
  metrics,:enlist "kdb_table_rows{table=\"ticker\"} ",string rows;
  
  / Safe Symbol Count
  syms:0;
  if[`sym in key `.; syms:count value `sym];
  metrics,:enlist "kdb_sym_count ",string syms;

  / Response
  .h.hy[`txt; "\n" sv metrics]
 };

-1 ">>> Prometheus Exporter loaded.";