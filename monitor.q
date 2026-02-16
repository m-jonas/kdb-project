/ monitor.q - Advanced Prometheus Exporter
/ Exposes metrics at http://localhost:PORT/metrics

/ 1. Explicitly define the MIME type for `txt to be text/plain
/ (This overrides any defaults to ensure Prometheus is happy)
.h.ty[`txt]:"text/plain";

.z.ph:{[x]
  if[not "/metrics"~first x; :.h.hy[`html; "Go to /metrics"]];

  / --- 1. System Stats ---
  w:.Q.w[];
  metrics:();
  metrics,:("kdb_mem_used_bytes ",string `int$w`used);
  metrics,:("kdb_mem_heap_bytes ",string `int$w`heap);
  metrics,:("kdb_global_vars ",string count key `.q);
  
  / --- 2. Client Stats ---
  / Count keys in .z.W (Active handles)
  metrics,:("kdb_client_count ",string count key .z.W);
  
  / --- 3. Data Stats (Safe Check) ---
  / Check if 'ticker' table exists before counting to avoid errors on startup
  rows:$[not null name:first `ticker intersect tables`.; count value name; 0];
  metrics,:("kdb_table_rows{table=\"ticker\"} ",string rows);
  
  / Check symbol count (Enum health)
  syms:$[not null name:first `sym intersect key`.; count value name; 0];
  metrics,:("kdb_sym_count ",string syms);

  / --- 4. Format & Send ---
  txt:"\n" sv metrics;
  .h.hy[`txt; txt]
 };

-1 ">>> Prometheus Exporter loaded (text/plain).";