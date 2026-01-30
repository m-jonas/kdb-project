### Start TickerPlant (TP) on WSL:

`q tick.q sym . -p 5010`

### Start RDB on WSL:

`q r.q -p 5011`

### Initiate manual EOD (For testing purposes):

`.u.end[.z.D]`

### Start CEP calculations:

1. Start TP: q tick.q sym . -p 5010
2. Start Feed: Run cb_feedhandler.py
3. Start CEP: Open a new terminal and run:
`q cep.q -p 5012`