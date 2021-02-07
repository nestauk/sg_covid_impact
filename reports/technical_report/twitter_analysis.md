---
title: "Twitter analysis"
header-includes: |
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega@5"></script>
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega-lite@4.8.1"></script>
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega-embed@6"></script>
---

<div id="vg-tooltip-element" class="vg-tooltip" style="top: 33px; left: 75px"></div>

# Data and methodology

In order to collect the tweets of Scottish businesses - they are not provided by Glass - we have built our own prototype pipeline to scrape the websites of Scottish businesses, find references to twitter accounts, and scrape the tweets of these accounts.

The scraper scrapes the main page of each business website,
 finds additional internal links and applies a simple heuristic to choose which links are the best $n$ ($n=4$),
 and then scrapes these links too.
References to twitter handles or links to twitter are captured and the frequency of each counted aggregated for each website.
Tweets that are not retweets are collected from January 2019 up to and including November 2020 (the date of data collection).
The full history of a user's tweets would be prohibitively slow -
 due to the Twitter API ratelimit .
Furthermore, for many accounts the full history would not be available as the Twitter API only allows retrieveal of the 3,200 most recent tweets.
Collection from January 2019 is a pragmatic balance between tweet availability; collection speed; and the utility of having a previous year's tweets to normalise activity against.
Once tweets are collected, one must determine which of the twitter accounts mentioned on a businesses' website is the best match.
Our matching heuristic for this is as follows:

- Discard any twitter accounts mentioned more than 5 times across all websites
- If there is only one match, consider that a match (high recall, low precision).
- If one of the candidate twitter accounts has a string similarity score of over 70% then choose as a match.
- If the twitter profile of one of the candidate twitter accounts, includes a link to the business website then choose as a match.

An informal verification suggests that this heuristic performs well; however taking this analysis beyond the pilot stage would require improvement of the heuristic when there is only one match.
    
# Analysis


<div class=altair s3_path="tweets_volume.json" static_path="tweets_volume.png" id="fig:tweets_volume">Weekly count of tweets over time
</div>

[@fig:tweets_volume] shows the weekly count of tweets over time.
Depending on the counting methodology used,
 there is either a large increase or a slight decrease in twitter activity over time. 
This is due to the fact that the twitter API limits its users to the most recent 3,200 tweets over time
 resulting in a bias towards seeing more activity near the end of a dataset.
To reduce this bias we can count tweets from accounts that tweeted in both the first and the last month of the dataset (red line).

<div class=altair s3_path="tweets_volume_stack_section.json" static_path="tweets_volume_stack_section.png" id="fig:tweets_volume_stack_section">Left: Number of weekly tweets by SIC section. Right: Proportion of weekly tweets by SIC section
</div>

[@fig:tweets_volume_stack_section] shows the number and proportion of tweets by SIC section.
This is shown for accounts tweeting in the first and last month of the dataset and accounts for which a SIC section could be obtained by matching its corresponding Glass organisation to companies house.
There are no large temporal dynamics across SIC sections.

<div class=altair s3_path="tweets_volume_stack_laua.json" static_path="tweets_volume_stack_laua.png" id="fig:tweets_volume_stack_laua"> Left: Number of weekly tweets by Council area. Right: Proportion of weekly tweets by Council area
</div>

[@fig:tweets_volume_stack_laua] shows the number and proportion of tweets by Council area.
This is shown for accounts tweeting in the first and last month of the dataset and accounts for which a trading address could be obtained by matching its corresponding Glass organisation to companies house.
There are no large temporal dynamics. across SIC sections.

<div class=altair s3_path="tweets_per_user.json" static_path="tweets_per_user.png" id="fig:tweets_per_user">Left: Distribution of tweets per user across all tweets.
Right: Distribution of tweets per user for accounts tweeting in the first and last month of the dataset
</div>

[@fig:tweets_per_user] shows the distribution of tweets per user across two different counting methods - 
counting all tweets and only counting tweets from accounts tweeting at the beginning and end of the dataset.
The distribution is significantly changed, with the latter appearing log-normally distributed. 
While only a small number of users have the maxiumum number of tweets, 3200,
due to their frequent tweeting they may contribute a disproportionate number of tweets in the months for which their tweets contribute.
To avoid the intricacies inherent in counting volume of tweets, we opt to compare compare proportions of tweets within a given timeframe when stratifying by factors such as sector, region etc. 

<div class=altair s3_path="tweets_new_users.json" static_path="tweets_new_users.png" id="fig:tweets_new_users">Left: New twitter users each year by SIC section.
Right: New twitter users each quarter (since 2019 Q1) by SIC section
</div>

[@fig:tweets_new_users] shows the number of new users over time, extracted from the account creation date in the tweet's user metadata.
We see that the majority of Scottish businesses in our dataset have been on Twitter for several years - 
 we see peak rates of adoption in the early 2010's with the number of new users decreasing each given year.
Whilst this constant decrease and the small numbers of new users since 2019 makes it hard to assess the extent to which businesses may have adapted to Covid-19 by adopting an online presence
 we do see a spike in the number of new users in April, May, and June 2020.
However, the evidence for this is extremely weak as we are talking about 10-15 new users!

<div class=altair s3_path="tweets_laua_representivity.json" static_path="tweets_laua_representivity.png" id="fig:tweets_laua_representivity">Over-representation factor of each Council area's share of tweets when compared to their presence in the Glass data
<!-- TODO: do this by user too -->
</div>

[@fig:tweets_section_representivity] shows how under or over-represented Council areas share of tweets are when compared to Glass.
We see that Edinburgh, Glasgow, and other urban areas are over-represented compared to rural areas which tend to be under-represented.

<div class=altair s3_path="tweets_section_representivity.json" static_path="tweets_section_representivity.png" id="fig:tweets_section_representivity">Over-representation factor of each SIC section's share of tweets when compared to their presence in the Glass data
<!-- TODO: do this by user too -->
</div>

[@fig:tweets_section_representivity] shows how under or over-represented SIC section's share of tweets are when compared to Glass. 
Perhaps as expected, *Accomodation and Food Services* are very over-represented.
*Information and Communication Services Activities*, and *Processional, Scientific, And Technical Activities* are under-represented likely due to their over-representation in the Glass dataset.


<div class=altair s3_path="tweets_last_tweet.json" static_path="tweets_last_tweet.png" id="fig:tweets_last_tweet">The date of the last tweet of each users account by SIC section
</div>

[@fig:tweets_last_tweet] shows that 64.2% of accounts tweeted in the last month of the dataset.
There is a hint of a small spike in more users stopping tweeting in March and April of 2020 when Covid-19 first impacted businesses; however a similar spike happens in 2019 so this could just be a coincidence.

<div class=altair s3_path="tweets_open_close_norm.json" static_path="tweets_open_close_norm.png" id="fig:tweets_open_close_norm"> Relative frequency of "open" or "close" being contained in a tweet's text when compared to the same week in the previous year
</div>

[@fig:tweets_open_close_norm] shows a large sharp spike in tweets containing "close" in the middle of March 2020 when the country first went into lockdown.
Half as many tweets mentioned "close" in the week of April 15; however this way due to an increase in tweets mentioning "close" in Easter 2019, rather than an effect from April 2020.
There is a large but wider peak in tweets containing "open" in June and July 2020, when restrictions were due to be lifted.
From October 2020, the number of tweets mentioning "close" rises again as more restrictions were imposed.
A peak in "close" in mid-February needs more investigation.

<div class=altair s3_path="tweet_section_stack_terms.json" static_path="tweet_section_stack_terms.png" id="fig:tweet_section_stack_terms">Proportion of a weeks tweets (across all SIC sections) mentioning various terms, plotted by SIC section
</div>

[@fig:tweet_section_stack_terms] shows the proportion of a weeks tweets mentioning various terms, plotted by SIC section.
"Brexit" is included in these terms to check whether terms may be correlated with Brexit uncertainty and disruption.
For example, *Transportation And Storage* businesses begin tweeting about delays in August 2020;
 however this could have been due to Covid-19 or Brexit.
The sectoral heterogeneity is immediately apparent:
 *Accomodation and Food Services* tweet about their offering of delivery and takeaway during the pandemic;
 other sectors such as *Education* and *Agriculture, Forestry And Fishing*, *Arts, Entertainment And Recreation* etc. tweet about "online";
 and *Agriculture, Forestry And Fishing* was the main sector talking about "brexit" (in 2019).
This simplistic term search is not without its drawbacks,
we do not see the context within which a term is used.
For example, Section E begins tweeting about "supply" from August 2020; however this section relates to Water Supply and is not likely to be talking about supply issues for a product/service.


<div class=altair s3_path="tweet_terms_stack_section.json" static_path="tweet_terms_stack_section.png" id="fig:tweet_terms_stack_section">Proportion of a weeks tweets mentioning a term by SIC section
</div>

[@fig:tweet_terms_stack_section] provides a complementary view to [@fig:tweet_section_stack_terms], grouping by term and then section rather than section then term.
We see many of the same patterns such as *Accomodation and Food Services* talking about takeaway and *Transportation and Storage* companies tweeting about delays from August 2020; however we now see that whilst a high proportion of *Agriculture, Forestry, And Fishing* tweets mention "brexit", the number of such businesses is very small.


<div class=altair s3_path="tweet_region_stack_terms.json" static_path="tweet_region_stack_terms.png" id="fig:tweet_region_stack_terms">
Proportion of a weeks tweets (across all Council areas) mentioning various terms, plotted by Council area
</div>

[@fig:tweet_region_stack_terms] and [@fig:tweet_terms_stack_region] provide a similar view to [@fig:tweet_section_stack_terms] and [@fig:tweet_terms_stack_section] but by Council area rather than SIC section.
Due to the dominance of Glasgow and Edinburgh, the trends for smaller council areas is noisy. 
Nonetheless we can pick out interesting aspects of regional heterogeneity,
 such as *Aberdeenshire* having a sharp peak in tweets mentioning "delay" around the first lockdown which then declines; and both *Edinburgh* and *Perth and Kinross* increasingly tweeting about "delay" from August 2020.
*Clackmannanshire* is the only Council area tweeting a lot about "open" during the first lockdown, though this is a small number of tweets.

<div class=altair s3_path="tweet_terms_stack_region.json" static_path="tweet_terms_stack_region.png" id="fig:tweet_terms_stack_region">
Proportion of a weeks tweets mentioning a term by Council area
</div>

# Discussion

We have built a proof-of-concept pipeline to identify and collect the twitter accounts of businesses by scraping their websites and investigated the viability of using this data to assess the impact of Covid-19 on Scottish businesses with a twitter presence.

Whilst available for a smaller number of businesses than the Glass notice data,
 the twitter data does not require licensing data from a 3rd party on an ongoing basis;
  is of a higher quality;
   and is broader than Covid-19.
In this pilot analysis we did not find robust evidence of an increased twitter presence due to Covid-19;
 however the tweets of businesses already on twitter provide a timely and granular indicator about what businesses are doing.
It is clear that this data could help policymakers assess understand how businesses are responding to an ongoing pandemic;
 however the value of this data beyond the current set of restrictions whilst likely high is unclear.
A potential scale-up option would be to put the twitter dataset into Elasticsearch to generate a search engine for the tweets of Scottish businesses which could be queried by policymakers to obtain lists of tweets relating to the query and interactive visualisations communicating the trends across 
 industry, space, and other factors;
 however input from policymakers about what specifically they would like to find from this data would be required to correctly scope this.

Regardless of the form a scale-up would take,
 there are several improvements to the pipeline that would be necessary. 
Chief among these would be: improving the ability of the scraping pipeline to detect and match twitter accounts,
 collecting retweets,
  and collecting tweets further back in time and for accounts with more than 3,200 tweets.
This future collection would likely require access to Twitter's [Academic research product track](https://developer.twitter.com/en/solutions/academic-research) which provides a more permissive and complete API for researchers.
