# Conclusions

In this section we revisit our initial goals for the project:

1. To gauge the opportunities that novel data sources and methods offer for tracking the impacts of the pandemic, as well as their limitations
2. To understand what these data tell us about economic exposure and opportunities to diversify away from Covid-19 in Scotland, and the implications for Scottish Government.
3. To assess options for building infrastructure for automated data collection, processing and visualisation that leverage the granularity and timeliness of novel data and their ability to inform economic policy decisions closer to real-time.

## Opportunities and limitations of novel data

Our results support the idea that novel data sources can provide valuable information about the impact of Covid-19. For example, business website data seems to be a useful source of text about industrial activities and the indicators of industrial exposure to Covid-19 based on the transformation of these industrial vocabularies into Google Search Trend data are consistent with qualitative and quantitative understandings of the impact of the pandemic based on official and novel sources such as the Google Footfall dataset. Our local indicators of exposure to Covid-19 and opportunities for diversification from it show an association with our proxies for Covid-19 impact based on claimant counts that suggests that they are capturing some signal about the vulnerability of different local economies to the shocks of Covid-19.

Our macro analysis bypasses key limitations of business website data by using the SIC taxonomy as a "lookup" with official statistics, helping us to generate policy-relevant measures of employment and reducing concerns about geographical and industrial biases in the Glass data which our coverage analysis suggests are in any case moderate. This comes at the cost of substantial aggregation and reliance on the SIC taxonomy which presents important limitations in terms of its lagginess, presence of uninformative industrial codes ("Other activities not elsewhere classified") and risk of heterogeneity in exposure to Covid-19 within large codes. One option to address this issue would be to generate estimates of sectoral exposure at a finer level of sectoral granularity. This would require additional search data collection via the cloud computing infrastructure we have developed to overcome some restrictions in the rate for using Google Search Trends API and would likely bring some noise into our measures. The reason for this is that the industrial vocabulary for some industries would have to be based on smaller samples of businesses subject to higher misclassification rates.

We have also explored various avenues to harness the granularity of the Glass data through an analysis of Covid-19 notices at the firm level, the collection of additional social media data from business websites, and by looking for ways to match the Glass data with business registers.

<!---
Alex add here about the opportunities of limitations of other sources
-->

## Implications

Our analysis of exposure and diversification to Covid-19 in Scotland suggests that the industrial composition of the country makes it slightly more succeptible to the economic impacts of Covid-19 than other parts of the UK: sectors related to tourism such as *Accommodation* and *Travel agencies* and cultural activities such as *Libraries and Museums* where Scotland has a relative specialisation are highly exposed to Covid-19 and have limited opportunities for diversification from it. 

This is reflected in important geograaphical heterogeneity in exposure to Covid-19. While council areas in the Highlands and Islands appear to be more exposed to Covid-19 because of the relative importance for their economies of industries such as those we described above, we also see council areas in other parts of Scotland showing high levels of exposure to the pandemic as a consequence of their industrial particularities. Two examples of this are City of Edinburgh at the onset of the pandemic because of its reliance on finance and professional services, and Aberdeen City and Aberdeenshire because of the importance of oil and energy industries that have, in some cases, limited opportunities for diversification into sectors which are less exposed to Covid-19. Local authorities in the South and Southwest which more manufacturing activity appear, in general, less exposed to the pandemic.

Our analysis of the evolution of normalised claimant counts at the council area level and their correlation with other secondary data suggests that wealthier local economies with better educated workforces have suffered a stronger shock from Covid-19. At the same time, these areas are likely to have access to the resources and capabilities to overcome this shock, not least the skills to diversify into industries that are less exposed to the pandemic. Many of the digitalised and knowledge intensive sectors that our analysis suggests are less exposed and more able to move into new markets are more important in those areas. An important challenge for policymakers will be to put in place interventions to support industries with less diversification opportunities whitstand the shocks of the pandemic while, at the same time, boosting their ability to transition into new industries while mitigating potential increases in inequality (many of the industries that are highly exposed to the pandemic and have low diversification opportunities are low skill, low salary and low productivity). This will be important for boosting Scottish' local economies resilience to Covid-19 in the short term, and to other future shocks linked to Brexit, automation and the environmental transition that may be coming down the line. The analysis that we have undertaken here underscores the potential of novel, high granularity data sources for informing such policies.


## Next steps

There are several avenues that we could follow in order to improve and expand our analysis of sectoral exposure and diversification from Covid-19, and to visualise its results.


### Aggregated analysis

Our industry vocabularies are based on the business website descriptions of all companies in the UK, which might miss products and services that Scotland specialises on within particular industries. We could address this by re-building the business vocabularies using only the descriptions from Scottish companies. One potential issue with this approach is that it would reduce the sample sizes we use to create industrial vocabularies potentially introducing noise in our results. In a similar vein, and as mentioned before, we could generate industrial vocabularies at a higher level of SIC resolution in order to capture more accurately the evolution of exposure in detailed SIC industries.

We have extracted Google Search trend data for all the UK under the assumption that these trends will be broadly aligned with the evolution of the situation in Scotland. We could however re-run our queries to extract search trends at the level of Scotland or even sub-national geographies. This might be particularly relevant for the analysis of exposure to Covid-19 in sectors with a strong level of local consumption such as for example food and beverage service activities, as well as differences between parts of the country under different social distancing restrictions.

On the modelling side, we have shown that present and lagged measures of exposure to Covid-19 and opportunities to diversify away from Covid-19 are linked to claimant count rate and normalised claimant count rate levels. One could explore different modelling strategies and additional data sources to attempt to nowcast claimant count rates. One challenge for thi effort is that - as we have shown throughout - the evolution of the pandemic and policy responses to it are quite volatile and could creaate structural breaks that hinder predictive analyses based on historical data.

Related to the above, we believe that it would be useful to incorporate additional secondary data and contextual variables about the state of local economies of Scotland and segmenting them into clusters in order to identify "local economy types" that may respond to Covid-19 shocks in different ways. 

Finally, we would like to incorporate additional secondary data into our analysis in order to further assess the reliability of our indicators. For example, ONS recently started releasing experimental statistics about business births and deaths by (highly aggregated) industries and region which we could compare with our indicators of exposure and opportunities to diversify from Covid-19. Along similar lines, we will analyse data about changes in the industrial composition of different locations based on BRES and IDBR data to gauge whether these changes are consistent with the indicators we have developed here (ie losses of employment in industries that are more exposed to Covid and gains in those that are less exposed or even positively exposed).

### Micro analysis

<!---
Alex adds stuff here
-->

### Visualisation options

In this project we have worked with datasets with a high degree of temporal, geographical and sectoral granularity. Although we have tried to showcase this richness through the interactive charts linked throughout the report, we believe that realising their potential requires the development of dedicated dashboards and interactive tools. These would display regularly updated information about the situation in Scotland and its local economies, opportunities for diversification and other contextual data. Combined with the subject expertise of policymnakers and practitioners, this would make it possible to identify and harness economic challenges and opportunities quicker and more accurately than is possible with data as currently presented.

 




 