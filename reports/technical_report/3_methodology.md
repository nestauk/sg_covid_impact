---
title: "3. Methodology"
bibliography: technical_report.bib
---

# 3. Data sources and methodology

This section describes the data we have collected and the methods we have deployed in its analysis in order to answer the following questions:

1. What is the role of business website and search data in generating new indicators about economic exposure to Covid-19 that add to what evidence is available from existing official and administrative sources? Here we are in particular interested in the technical feasibility of various approaches to data collection and processing, and on the quality of the resulting data in terms of coverage and accuracy.
2. What do the resulting indicators tell us about the impact of Covid-19 on Scotland? Here we are particularly interested in identifying what local economies / sector firms / firms in Scotland are most exposed to Covid-19, what are their opportunities for diversification and implications for policy.

We begin with a high level summary of our approach, followed by a detailed description of each of the data sources we have collected, how we have processed and their validation through triangulation with other sources and previous studies. All the code we have developed for data collection and analysis is available from [this GitHub repository](https://github.com/nestauk/sg_covid_impact/). 

## 1. The logic of our approach

The starting point for our analysis is that business websites contain information that may be relevant for the analysis of the economic impact of Covid-19. This includes descriptions of what businesses do which may help us to quantify their exposure / opportunities to diversify from Covid-19 and Covid-19 notices where businesses describe how they are adapting in response to the pandemic. It is possible to deploy machine learning and natural language processing methods in order to extract information from these unstructured sources.

At the same time, business websites are hard to use for longitudinal analyses because they do are not updated following a regular schedule, they lack policy-relevant information about employment and turnover, and suffer from potential biases in their sectoral and geographical coverage.

Our prior is that some of these limitations can be addressed by combining business website data with other sources:

1. We can use Google Search trend data queried with the names of products and services that businesses sell (extracted from their business descriptions) to build a longitudinal picture of exposure to Covid-19. We can also extract social media profiles from business websites and use them as a seed to collect their social media feeds in order to generate more regularly updated measures of their activity. 
2. We can combine measures of sectoral exposure to Covid-19 based on the text from business websites with official data to estimate the share of workorce in local economies that is exposed to Covid-19. This is similar to the approach in [@del2020supply, @mcintyre2020vulnerability, @enenkel2020cities] but with the advantage of relying on data-driven measures of sectoral exposure to Covid-19 derived from search trends, instead of ex-ante expert assessments or irregularly, low-granularity sector exposure data.
3. We can use the text in business websites to generate maps of "sectoral proximity" helping us to identify opportunities for industrial diversification away from markets that are highly exposed to Covid-19. We can use the results to rank the position of different sectors in terms of their ability to diversify away from Covid-19, and combine this with official data to measure the extent to which different local economies have large shares of their workforce employed in sectors that are highly exposed to Covid-19 and have limited opportunities to diversify away from it.
4. We can combine business website information with the business registry in order to track business outcomes (such as business failure) ane explore opportunities to "nowcast" them using their text and Covid-19 notices as predictorrs (the idea being that there may be some signal about a business' outcomes in the text that describes current behaviours in response to the pandemic). 

Figure [@fig:pipeline] summarises our approach.

![Figure 1](https://raw.githubusercontent.com/nestauk/sg_covid_impact/80_reporting/reports/technical_report/pipeline_1.png){#fig:pipeline}

## 2. Data sources

### a. Glass.ai

The core dataset for our analysis has been obtained from [Glass](https://www.glass.ai/), a startup that uses machine learning to collect and analyse business website data at scale. More specifically, Glass begin from the universe of UK websites in web domain registers, identifies those that are highly likely to belong to a business, and extracts relevant information about them including their description, postcodes and sector based on an industrial taxonomy developed by LinkedIn. In this project, we work with information about 1.8 million business websites (which according to Glass account for 90% of UK business websites) collected in May and June 2020. 

The main advantage of Glass data that makes it relevant for our project is that it includes business descriptions that can be used to understand their economic activities at a higher level of resolution than is possible using industrial taxonomies. The fact that businesses generally use their websites to promote goods and services to consumers mean that we would expect their terminology to be suitable for querying with Google Search Trends, the data source that we will use to proxy consumer interests for the goods and services provided by different industries and its evolution.

In addition to business metadata, Glass also started collecting Covid-19 notices at the beginning of the pandemic...

<!---
Alex adds info about Covid notices here
-->

### b. Google Search Trends

Google Search Trends is a Google service that provides aggregate information about the level of Google Search user interest in different search terms, which could be understood as a proxy for the subjects (including products and services) that those terms refer to. Google Search Trends has been extensively used in scholarly research. Some notable examples include its use to nowcast economic indicators [@choi2012predicting], to measure the impact of racial animus in US presidential elections [@stephens2014cost] and to forecast the incidence of influenza in the USA [@dugas2013influenza] \(this application also demonstrated its flaws as a data source when changes in user behaviour degraded the performance of searching for flu-related terms as a predictor of flu [@lazer2014parable]). More recently, journalists have used Google Search Trends to [measure Covid-19 impact on consumer lifestyle](https://www.economist.com/graphic-detail/2020/08/08/covid-19-seems-to-have-changed-lifestyles-for-good).

We collect search volume data for a set of keywords extracted from business websites using the procedure described in Section 3.b. In order to query the Google Search API we rely on [GTAB](https://github.com/epfl-dlab/GoogleTrendsAnchorBank) (Google Search Trends Anchorbank), a Python package that generates, for a selected period, a "bank" of anchor terms with a range of popularities that is then used to calibrate search volumes for all keywords of interest subsequently queried according to a common scale [@west2020calibration]. We extract search trend data for UK searches in the period between 1 Jan 2019 and 1 February 2021 (we will use the 2019 data to normalise search volumes post-pandemic). 

### c. Twitter

<!---
Alex adds info here
-->

### d. Miscellaneous secondary sources

#### Official sources

Our analysis makes extensive use of official sources obtained from Nomis, a website offering access to open labour market statistics in the UK. We collect:

* Data about Local Authority District levels of employment at the SIC-2 (Division) level from the [Business Register Employment Survey (BRES)](https://www.nomisweb.co.uk/sources/bres) for the most recent year available (2019).

* [Claimant count](https://www.nomisweb.co.uk/sources/cc) data including information about people claiming Jobseekers Allowance or Universal Credit at the Local Authority District level. We collect monthly data on claimant count rates (claimant numbers normalised by working age population) for 2019 and 2020 and normalise monthly 2020 values by their 2019 equivalent in order to capture changes linked to Covid-19.

* Employment and Economic Activity rates and percentages of the population with tertiary education and no education at the Local Authority District level from the December 2020 release of the [Annual Population Survey](https://www.nomisweb.co.uk/sources/aps).

* Medial annual gross income data from the Annual Survey of Hours and Earnings ([ASHE](https://www.nomisweb.co.uk/sources/ashe)).

#### Other validation sources

We have collected additional data from a number of secondary sources which we use to triangulate our trends results. They include:

* [Google community mobility data](https://www.google.com/covid19/mobility/) which report disaggregated information about phone user mobility across different categories of places such as retail and recreation, groceries and pharmacies, parks, transit stations, workplaces, and residential.
* [Covid incidence data](https://coronavirus.data.gov.uk/) including new deaths attributed to Covid-19 within 28 days of diagnosis which we obtain from `data.gov.uk`.

### e. Business registry sources

<!---
Alex explains why there were no suitable sources
-->

## 3. Data processing

### a. Matching Glass with Companies House

<!---
Alex adds description of fuzzy matching here
-->

### b. Creating an industrial vocabulary

In order to query Google Trends, we need a list of keywords related to the economic activities of different industries. We extract this "industry vocabulary" from Glass business descriptions. Our strategy is to aggregate the descriptions of all businesses in the same SIC division, tokenise then (extract individual works and commonly occurring combinations of words), count them and normalise these counts by the word distribution over the whole corpus. Having done this, we remove duplicate words (eg plurals) and focus, for each division on the top 25 / those that have a salience score above one (ie are overrepresented in the division) after removing tokens with less than 75 occurrences in each division to avoid low-frequency noisy terms.

Table \ref{tab:examples} presents examples of industrial vocabularies randomly extracted from our list of SIC divisions. It shows that in general the approach we have taken appears to work well and generates intuitive vocabularies for various divisions, although in some cases such as with division 21 (pharmaceuticals), it generates very few keywords, potentially reducing the robustness of our search analysis for those sectors.

<!---TODO: calculate % employment accounted by industries with short industry vocabularies - it will be low.
--> 

|Division									|Keywords|
|------------------------------------|----------------------|
|41: Construction of buildings      	|homes building housing apartments construction builders finish extensions residential projects new\_build decorating architects planning_permission developments      |
|38: Waste collection, treatment and disposal activities| materials recovery recycling waste clearance scrap environmental skip\_hire asbestos skips metals disposal waste\_disposal scrap\_metal waste\_recycling waste\_management landfill |
|58: Publishing activities 				|news games books press magazine journal editor fiction literature titles publishing articles writers readers authors|
|21:Manufacture of basic pharmaceutical products and pharmaceutical preparations | health business also|
|80:Security and investigation activities | police security cctv sia investigation guards alarms locksmith surveillance security\_systems access_control fire\_security security\_guards |
|25:Manufacture of fabricated metal products, except machinery and equipment | metal steel engineering wire gates stainless\_steel aluminium components assembly welding precision cnc aerospace fabrication sheet\_metal | 

Table: Industrial vocabulary examples by SIC division \label{tab:examples}

### c. Estimating sectoral exposure

We extract normalised search volumes for keywords in industry vocabularies from Google Search Trends and use the results to produce measures of industrial exposure to Covid-19. In order to do this we:

1. Take weekly search volumes by keyword to generate monthly averages.
2. Normalise the search volume of each keyword by its salience in a SIC division. This means that keywords that are more salient for the industry will have a stronger weight when estimating its exposure to Covid-19 than terms that are less salient (ie occur more frequently in other divisions). For example, in Division 25 in table \ref{tab:examples} `metal` will be more salient (and have more weight when estimating that division's exposure to Covid-19) than a generic term such as `components`.
3. Normalise search volumes by the total volume of searches in the industry vocabulary. This means that keyords that account for a larger proportion of all searches in an industry vocabulary will have a bigger weight in determining its exposure to Covid-19.
4. Rescale 2020 and 2021 normalised keyword search volumes by the normalised search volumes in equivalent 2019 months in order capture deviations from a pre-Covid-19 baseline and account for seasonality in searches (ie the fact that people are more likely to search for information about air transport when they are planning their holidays at the beginning of the year, or for information about sports when a tournament starts).
5. Calculate the average of 2019-rescaled keyword search volumes in a division weighted by the share of division search accounted by that keyword. 
6. The procedure above yields a single monthly score for each SIC division capturing the extent to which search trends about keywords related to it are higher or lower than the pre-Covid 19 average. We change the sign of the score and quantize this series into deciles: we label sectors in the highest deciles as "highly exposed to Covid-19" (ie the weighted search volumes for their queries are much lower than the pre-Covid-19 baseline) and generally focus on them through our analysis.

### d. Calculating sectoral diversification options

We use similarity between business website descriptions in order to calculate similarities between industries, which we interpret as a proxy for diversification opportunities: those sectors that are "close" to each other within the industry space that we build are more likely to be able to diversify into each other activities (this idea is based on the "Principle of Relatedness" which economic geographers have shown shapes the evolution of local economies [@hidalgo2018principle]).

In order to calculate similarities between industries we train a machine learning model that predicts the SIC divisions for companies in the Glass-Companies House matched dataset using their descriptions. We use grid-search to select the model type and parametres that yield the best predictive performance, resulting in a regularised logistic regresssion. 

Since this model is trained using a one vs rest classification regime that generates a probability score for each business and SIC division, we can use the resulting vector to calculate "industry co-occurrences" in a company (ie companies that are predicted to belong to more than one sector based on the machine learning model). 

We create a network (the "industry space") where the nodes are SIC divisions and the edges are co-occurrences in business descriptions (the degree or thickness of these edges depends on the number of co-occurrences) and arrange it using a force-directed algorithm that bundles more closely those nodes which are similar to each other. In order to simplify our visualisations, we will use a maximum spanning tree algorithm that preserves those edges that create a fully connected network with the highest-degree edges and add to it the top 100 weighted-edges which are not part of the maximum spanning treee (this is the same approach that [@hidalgo2009building] use to the

### e. Topic modelling Covid notices

<!---
Alex adds info here
-->


## 4. Validation

### a. Glass coverage

### b. Descriptive results

### c. Correlation betweeen sectoral exposures and other measures of Covid-19 impact

### d. Qualitative validation