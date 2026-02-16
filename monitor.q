/ monitor.q - Universal Prometheus Exporter

/ 1. Force text/plain for `txt
.h.ty[`txt]:"text/plain";

/ 2. Initialize Message Counter
if[not `msgs in key `.mon; .mon.msgs:0];

/ 3. Universal Function Wrapper
/ Tickerplant uses .u.upd | RDB uses upd (global)

/ Case A: Tickerplant (.u.upd)
if[`upd in key `.u;
    if[not `upd_orig in key `.u;
        .u.upd_orig:.u.upd;
        .u.upd:{[t;x] 
            .mon.msgs+:1;
            .u.upd_orig[t;x]
        };
        -1 ">>> Monitor: Wrapped .u.upd (TP Mode)";
    ];
];

/ Case B: RDB/CEP (global upd)
if[`upd in key `.;
    if[not `upd_orig in key `.;
        .upd_orig:upd;
        upd:{[t;x] 
            .mon.msgs+:1; 
            .upd_orig[t;x]
        };
        -1 ">>> Monitor: Wrapped global upd (RDB Mode)";
    ];
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
  
  / --- Safe Table Counts ---
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

-1 ">>> Prometheus Exporter loaded.";