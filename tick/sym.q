/ BTC-USD Ticker Schema
ticker:([] 
    time:`timespan$(); 
    sym:`symbol$(); 
    price:`float$(); 
    size:`float$(); 
    bid:`float$(); 
    ask:`float$(); 
    bidSize:`float$(); 
    askSize:`float$()
    )