# Summary
We are academic economic researchers looking at the role of autobidder systems in the Australian Energy Market. We are investigating publically available data at [this](https://www.nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2025/MMSDM_2025_01/MMSDM_Historical_Data_SQLLoader/) link. The [data](https://www.nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2025/MMSDM_2025_01/MMSDM_Historical_Data_SQLLoader/DATA/) directory has many zip files and I do not understand what each file contains. I need a comprehensive summary and understanding of what is in every data file available on the data page so I can download the data necessary for my project.

## Data required
Our project entails observing daily bids for 5 minute periods for each day. We need the bid price and quantity bands for each firm for the Ancillary Services (FCAS) in the NEM. We also need bid price and quantity bands for the Energy market, because that's often how batteries buy energy to charge up. My understanding is that the NEM market is divided into 5 sub regions. In times of congestion, the market clearing price will be different across them all. Arbitrage should keep the market clearing price similar at non-congestion times. I need to identify the market clearing price for each sub region for every auction that's cleared for every market.

## Questions about NEMWEB Data
There seem to be many files labelled as "constraint" in the data. 
1. What are these constraint data files?
2. Are there any files that contain demand forecasts?
3. Are there fees for participating in these auctions?
4. What are the exact market rules for these FCAS auctions?
5. Is there dat aon the geographic location for each market participant?
6. Do participants submit bids for specific regions, or do they just submit it to the entire market and the system operator decides which market they take part in?

## Documentation Links
[This](https://www.nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2025/MMSDM_2025_01/MMSDM_Historical_Data_SQLLoader/DOCUMENTATION/MMS%20Data%20Model/v5.4/) page seems to have documentation on the data packages. 
You should also check the web for any other potentially helpful resources on answering these questions.

## Outputs
You should output the following files
1. A markdown file in the projects documentation directory for a description of what every data file on [this](https://www.nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/2025/MMSDM_2025_01/MMSDM_Historical_Data_SQLLoader/DATA/) contains and if it would be helpful for this project.
2. Another markdown file of things that were uncertain and questions you have, or things that you couldn't answer. This markdown file should also contain answers to the questions I list above.

The assumptions and methodology used to answer and construct all of these files should be included in all files. If any documentation is found online that is relevant, it should be linked and the relevant sections answering my questions should be highlighted.