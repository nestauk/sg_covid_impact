---
title: "Using web data and data science methods to map the economic impact of Covid-19 in Scotland"
header-includes: |
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega@5"></script>
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega-lite@4.8.1"></script>
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega-embed@6"></script>
---
# 1. Introduction

Covid-19 has impacted economies across the world through a supply shock - lockdowns prevent some businesses from operating or greatly decrease their productive capacity - and a demand shock - economic actors have altered their consumption and investment behaviours in response to the pandemic. A firm's exposure to these shocks depend on the nature of its processes, products and services: Can its employees work from home? Can its products be sold online? Some firms may be able to diversify into economic activities that are less exposed to Covid-19, perhaps exploiting growing demand for products and services in adjacent markets. 

Policymakers need relevant, granular and timely data about these phenomena in order to inform policies to mitigate the effects of economic exposure to Covid-19 and harness the opportunities to diversify (at least in the short term) towards markets that have been less disrupted by the pandemic. In recent months this has involved a combination of official data from business surveys, small-scale business panels, administrative data tracking the impact of Covid-19 on unemployment, and a wide range of novel ("big") data sources such as online job ads, credit card transaction and mobility data and information obtained from business websites. 

Here, we report the results of a pilot study conducted for Scottish Government where we have combined official, administrative, business website and search data in order to measure the exposure and diversification opportunities to Covid-19 of different sectors, places and firms.  

Our goals are three-fold: 

1. To gauge the opportunities that novel data sources and methods offer for tracking the impacts of the pandemic, as well as their limitations, stemming for example from biases in their coverage and noise in their content.
2. To understand what these data tell us about economic exposure and opportunities to diversify away from Covid-19 in Scotland, and the implications for Scottish Government.
3. To assess options for building infrastructure for automated data collection, processing and visualisation that leverage the granularity and timeliness of novel data and their ability to inform economic policy decisions closer to real-time.

The structure of the report is as follows:

Section 2 contains a brief review of relevant studies about the economic impact of Covid-19 paying special attention to those that have used novel data sources like the ones that are deployed here, and analyses of the economic impact of Covid-19 in Scotland on which we will be building with the evidence that we create through our analysis.

Section 3 outlines our data sources and methodology for data collection and processing.[^1] It also contains some descriptive results and triangulation with other resources that speak to the strenghts and limitations of our sources.

[^1]: All the code that we have developed in the project is available from [this GitHub repository](https://github.com/nestauk/sg_covid_impact).

Section 4 presents our findings structured in two sub-sections that respectively focus on evidence about exposure and opportunities to diversify from Covid-19 at the aggregate level (considering sectors and local economies) and at the firm-level. 

Section 4 concludes with a discussion of the implications of our analysis and next steps.
