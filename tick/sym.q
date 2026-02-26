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

/ ITCH Level 2 Best Bid/Offer
bbo:([] time:`timespan$(); sym:`symbol$(); bidSize:`long$(); bidPrice:`float$(); askSize:`long$(); askPrice:`float$());

/ Algo Trading Signals
signals:([] time:`timespan$(); sym:`symbol$(); side:`symbol$(); qty:`long$(); price:`float$());