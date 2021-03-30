---
title: "Using web data and data science methods to map the economic impact of Covid-19 in Scotland"
subtitle: "A pilot study"
author:
	- "Alex Bishop"
	- "Juan Mateos-Garcia"
date:
	- 9 February 2021
fontfamily: times
figPrefix:
  - "figure"
  - "figures"
tblPrefix:
  - "table"
  - "tables"
secPrefix:
  - "section"
  - "sections"
---

# Executive Summary


In this technical report we explore the opportunities and challenges for using novel data sources and data science methods to measure the economic impact of Covid-19 in Scotland and its local economies. Our goals are to:

1. Assess the technical feasibility of implementing these methods
2. Validate the quality of the resulting indicators
3. Explore the results and consider their policy implications

## Data collection and processing

Our starting point is a database with information about 1.8 million businesses in the UK provided by Glass, a business intelligence startup. We enrich and process this data by:

1. Matching it with Companies House
2. Using business descriptions in websites to generate a vocabulary of industry terms and analyse their popularity in Google Searches compared to a pre-pandemic baseline, helping us to estimate measures of sectoral exposure to Covid-19
4. Combining it with secondary official sources to measure shares of employment in sectors exposed to Covid-19 in different countries and council areas, and the link between exposure and diversification opportunities and local Covid-19 impacts proxied with claimant count data
5. Generating measures of sector similarity based on business descriptions in order to identify diversification opportunities
6. We use topic modelling to analyse $400000$ Covid-19 notices posted in business websites in May and June 2020.
7. We extract twitter ids from Scottish business websites and collect their tweets (subject to restrictions in Twitter API) since January 2019 with the goal of analysing levels of activity and participation and the presence of keywords related to pandemic (and brexit) related shocks.
8. We explore potential data sources about business failure that could be correlated with our firm-level dataset in order to identify business behaviours that may be predictive of failure


## Results

#### Sectoral exposure and diversification

* The values of our web-based indicators of sectoral exposure to Covid-19 are consistent with qualitative understandings of the impact of the pandemic: sectors such as Accommodation, Air Transport, Creative Arts and Entertainment and Food and Beverage Service Activities appear to be most exposed while Computer Programming activities, Waste Collection and Publishing appear least exposed.
* The evolution of employment highly exposed to Covid-19 reflects the evolution of the pandemic and policies to tackle it such as lockdowns and social distancing measures, with peaks of exposure between April and the Summer, beginning of Autumn and Christmas.
* The share of employment exposed to Covid-19 in Scotland is similar to the rest of the UK but Scotland is specialised in sectors that have fewer opportunities to diversify away from Covid-19 impacts such as Accommodation, Libraries and Museums or Travel Operators and Renting and Leasing. 
* When focusing on the situation in local economies, we find that in general rural economies in the Highlands as well as some of the Islands have a greater share of their workforce exposed to Covid-19 because of their reliance on sectors related to travelling and tourism. Some urban areas such as City of Edinburgh or Aberdeen City are highly exposed to the pandemic for different reasons such as the respective importance of professional services and creative arts and entertainment, and land transport and oil.
* Our measures of Covid-19 impact based on (unemployment benefit) claimant count rates normalised against a pre-Covid 19 baseline show that wealthier and more educated council areas have suffered a relatively stronger shock from the pandemic. At the same time, these areas specialise in knowledge intensive sectors that may be better able to diversify into activities less exposed to the pandemic. 
* Our regression analysis finds a strong and positive link between share of a employment in a local economy in sectors that are highly exposed to Covid-19 and sectors with limited opportunities for diversification from Covid-19 (both derived from our web-based indicators), and monthly claimant count rates after adjusting from other factors. This supports the idea that our indicators are informative local economy vulnerabilities to the pandemic.
* An experimental predictive analysis where we use these models to estimate claimant count rates in January 2021 suggests generalised increases across council areas in Scotland potentially as a consequence of the Christmas lockdown. When we compare these predictions with actual claimant count data released in 2021, we find that they generally underestimate claimant counts, highlighting the severity of the economic impacts of the pandemic particularly during the Christmas period.

#### Covid-19 notices

* Our analysis of Covid-19 notices in business websites reveal a host of quality issues that make them difficult to analyse. More specifically, some of the notices are unrelated to Covid-19, their text is ambiguous and their length is variable. Notwithstanding this noise, Covid-19 notices might be useful for policymakes interested in tracking firm-level responses to the pandemic if they were collected in real time and distributed through interactive and explorable tools.

#### Twitter

* We study the evolution in the levels of Twitter activity by Scottish companies in different sectors and locations paying special attention to tweets mentioning terms related to the pandemic and its aftershock such as "open", "closed", "delay" and "furlough". 
* The trends revealed by this analysis seem to track the evolution of the pandemic (with for example spikes in tweets mentioning "closure" around the March lockdown) and responses by different sectors (eg transport companies talking about delays, accommodation and food service companies talking about delivery).
* There is also the possibility to track the impact of other events such as Brexit.

#### Firm-level outcomes

* Our scoping of firm-level sources of information about business failure such as Companies House fail to reveal any suitable options. Most sources are available at a high level of sectoral and geographical aggregation making them unsuitable for our purposes.
* Even more substantially, government policies to suppress business failure during the pandemic, for example through the furlough and business lending schemes, have artificially kept business failure rates low, making it difficult to estimate Covid-19 impacts through that proxy.

## Implications and next steps

#### Technical feasibility

* Our work yields proof-of-concept pipelines for the generation of industry vocabularies, analysis of their trends via Google Search, modelling of sector similarities and identification and extraction of business profiles, all using Glass data as a starting point in terms of business descriptions and links to websites.
* It would be technically feasible to scale up these pipelines in order to provide regular updates of analyses such as those presented in this report.
* There currently are no public sources of firm-level outcomes that could be used to analyse Covid-19 impacts at that level of resolution, or to predict firm-level outcomes using our leading Covid-19 exposure and diversification indicators. One option would be to use firm surveys such as the Business Impacts of Covid-19 (BIC) panel as a labelled dataset to train predictive models but this would require matching it with our data.

#### Indicator quality

* Our analysis and qualitative and quantitative validation of sector exposure and diversification measures suggest that the indicators based on business descriptions and Google Search Trends are informative about the evolution and impact of the pandemic.
* The quality of Covid-19 notices is variable making them hard to analyse using topic modelling methods. This casts doubts on the quality of the indicators and their suitability for policy without additional work to filter and label notices.
* An initial exploration of Twitter trends suggest that this source could provide highly granular and timely information about the impact of the pandemic (and other economic shocks such as Brexir) with a high degree of timeliness and resolution. Obviously, this kind of analysis would only be relevant for the sample of firms with websites that are active in Twitter, which is not representative of the Scottish business population. 

#### Policy implications
* The analysis of sectoral / local exposure to Covid-19 highlights the challenges to rural and islands economies with a strong presence of industries with limited opportunities to diversify from Covid-19.
* We note the heterogeneity of channels through which Covid-19 impacts in local economies and the fact that a diverse set of council areas such as City of Edinburgh, Aberdeen City or Stirling appear highly exposed at different moments of the pandemic. The indicators we have developed could help policymakers track this exposure closer to real-time and understand its link with the sectoral composition of different local economies in Scotland, thus informing policies better tailored to the local context and challenges.
* Wealthier and more educated areas seem to have suffered a most substantial impact from Covid-19 compared to a 2019 baseline but they may be in a better position to withstand this shock. Having said this, it is likely that there will be differences in exposure and resilience to Covid-19 across local industries and social groups in those areas. Policymakers should pay attention to Covid-19 impact in inequalities inside council areas as well as inequalities between these areas and others where the relative impact of Covid-19 may be lower but there are fewer resources and capabilities to diversify into sectors less exposed to the pandemic or mitigate its impacts.

#### Next steps

* There are many potential improvements and extensions to the data collection and processing activities that we have reported here that could result in more precise, granular and reliable indicators. 
* The high dimensionality of the data we have presented makes it specially suitable for dissemination through interactive tools and dashboards that are regularly updated, and where users can explore the data in order to identify interesting and useful patterns and trends, including firm-level information which could inform stakeholder engagement activities and targeted interventions. In this project we have developed a proof-of-concept infrastructure that, if scaled-up, would provide the foundation for that effort.
* Current vaccination efforts suggest that the end of the first and most dramatic phase of the pandemic may be in sight, perhaps reducing the need for such a tool. Having said this, we believe that the analysis we have presented here, if scaled up into a system for real-time-data collection and analysis could provide a valuable source of economic intelligence for Scotland's policymakers about the situation and evolution of local economies in Scotland, and their options to diversity and respond to new shocks that may happen in the future.
