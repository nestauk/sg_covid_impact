---
title: "Notice analysis"
header-includes: |
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega@5"></script>
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega-lite@4.8.1"></script>
  <script type="text/javascript" src="https://cdn.jsdelivr.net/npm//vega-embed@6"></script>
---



# Data

In addition to business metadata, Glass also started collecting Covid-19 notices at the beginning of the pandemic by searching for passages of text in a business' website that reference terms such as "Covid", "Coronavirus", "Government recommendation", "lockdown" etc.
This captures notices such as,

> "COVID-19: In light of the COVID-19 pandemic, we're only doing one-to-one lessons via Zoom or Skype. Please see our prices or contact us for more information. All the best, Dave and the team."

We have between 210K-220K such notices for each of May, June, and July 2020 which we have used to assess whether periodic collection of notices can help to assess the impact of Covid-19 in Scotland, by identifying sectors and regions which are posting notices that are indicative of exposure to Covid, such as only being able to conduct lessons online.

The SIC code (sector) of a notice is obtained by linking Glass to Companies house [@sec:], and regions can be obtained either from the address data scraped from a business' website or from the trading address listed in Companies house.

# Methodology

## Pre-processing

To turn the notice text into data we can mathematically analyse, we process the notices according to a multi-step process:

1) Split each notice into token
2) Filtering out tokens that are: URL's, XML, HTML, twitter-like social media handles, english stop words, or do not contain at least one ASCII letter
3) Filter tokens occurring less than ten times in the corpus
4) Construct tri-grams
5) Lemmatise tokens
6) Filter tokens that are two characters or less and n-grams that comprise solely of stop words
7) Filter tokens occurring less than ten times or in more than 90% of documents

For example the following notice, 

> "Leek Town Council has shown its support for a vital element in the town's response to the Covid 19 crisis by awarding a grant of £1000 to the Haregate Community Centre. Although the centre is now closed to its usual community groups, it has Read More..."

Becomes the following set of tokens

`['leek', 'town_council', 'has_shown', 'support', 'vital', 'element', 'town', 'response_to', 'covid_crisis', 'awarding', 'grant', 'community_centre', 'although', 'centre', 'closed', 'usual', 'community_groups', 'read_more']`

## Topic modelling

By considering our documents (business notices) as being a mixture of topics - a weighted mixture of words - we can learn topics in an unsupervised manner from the likelihood of word co-occurrences within our documents.
This approach enables us to analyse both the extent to which topics co-relate with factors such as the sector and location of notices, and identify whether any topics correlate with measures of exposure.

The most widely used and well known topic model is Latent Dirichlet Allocation (LDA) [@LDA]; however LDA is known to be unable to capture the full statistical properties of real-world corpora.
By representing text corpora as a bi-partite network of documents and words [@topSBM] exploited a mathematical connection between topic models and finding community structure in networks--namely the mathematical equivalence between the Stochastic Block Model (SBM) and probabilistic Latent Semantic Indexing (pLSI)--to develop an approach to topic modelling by deriving a non-parametric Bayesian parametrisation (topSBM) of pLSI adapted from a hierarchical SBM (hSBM) [@SBM].
We use this "TopSBM" approach to topic modelling as it confers multiple advantages over LDA such as automatically selecting the number of topics; yielding a hierarchy of topics; and permitting a more heterogeneous topic mixture than is permitted by LDA.

# Results

## Descriptive

Before presenting the results of the topic modelling we first explore in what Scottish regions and in what sectors notices appear, and compare these to their frequency in the base Glass datasets of business descriptions.

<div class=altair s3_path="notice_proportion_scottish_laua.json" static_path="notice_proportion_scottish_laua.png" id="fig:notice_proportion_laua">Proportion of notices in each Scottish council area compared to the baseline occurrence within the Glass dataset. Areas with a higher proportion of notices than baseline are more likely to have posted a notice than would be expected and vice versa.
</div>

Figure [@fig:notice_proportion_laua] shows that as well as being responsible for the source of a large proportion of both organisation descriptions and Covid-19 notices, business websites in Edinburgh and Glasgow were noticeably more likely to post notices than would be expected.

<div class=altair s3_path="uk_vs_scotland_notices_by_section.json" static_path="uk_vs_scotland_notices_by_section.png" id="fig:notice_proportion_section">Proportion of notices by SIC section each month compared to the baseline proportion of organisations in the Glass dataset - split by both Scotland and the whole UK. Sections with a higher proportion of notices than baseline are more likely to have posted a notice than would be expected and vice versa.
</div>

Figure [@fig:notice_proportion_section] paints a more interesting picture.
Construction business websites were much less likely to post notices than would be expected.
Whilst this could be because construction companies were less likely to have been impacted by Covid from May, the more likely explanation is that construction company websites are not where clients of these companies go to get information - updates are likely to come through more channels.
One surprising feature of this figure is that Wholesale and Retail Trade business websites were more likely to post notices than expected at the level of the UK; however Wholesale and Retail Trade business websites in Scotland were less likely.
Similarly, business websites engaging in Professional, Scientific, and Technical activities were much less likely to post notices across the whole of the UK than those websites that were in Scotland.
Another noticeable difference between Scotland and the UK is that Education business websites in Scotland did not post notices as frequently as across the whole of the UK, perhaps due to differing policies between Scotland and other home nations.

## Topic modelling

In this section we present the results of performing topic modelling on the notices of Scottish businesses.

[@tbl:topsbm_hierarchy] shows the topic hierarchy obtained. Topic level 3 was chosen as the level of analysis as the four topics yielded at level 4 are too broad and the 147 topics of level 2 are too fine.

| Level | Number of topics | Number of clusters |
| ----- | ---------------- | ------------------ |
| 0     | 2136             | 1995               |
| 1     | 805              | 753                |
| 2     | 147              | 160                |
| 3     | 30               | 28                 |
| 4     | 4                | 8                  |
| 5     | 1                | 1                  |
: TopSBM model hierarchy. {#tbl:topsbm_hierarchy}


### SIC section 

Initially we focus on analysing the outputs of the topic model at the section level of the SIC taxonomy.

<div class=altair s3_path="scotland_topic_activity_level_3_norm_by_sector.json" static_path="scotland_topic_activity_level_3_norm_by_sector.png" id="fig:topic_by_sector_norm_sector" height="50%">Topic activity (3rd hierarchy level) by SIC section. Topics are normalised such that the topic activity for each sector sums to 1.
</div>

Figure [@fig:topic_by_sector_norm_sector] shows the levels of topic activity - i.e. - for each topic-SIC section combination where activity has been normalised such that the activities for each sector sum to one. This highlights which topics each sector is more likely to talk about. 
For example, Manufacturing has an activity of 0.38 in topic zero meaning that 38% of topic activity for Manufacturing businesses relates to topic zero.
We see that four topics (0, 3, 6, 8) dominate the activity of most sections.

<div class=altair s3_path="scotland_topic_activity_level_3_norm_by_topic.json" static_path="scotland_topic_activity_level_3_norm_by_topic.png" id="fig:topic_by_sector_norm_topic" height="50%">Topic activity (3rd hierarchy level) by SIC section. Topics are normalised such that the topic activity for each topic sums to 1.
</div>

Figure [@fig:topic_by_sector_norm_topic] shows the levels of topic activity - i.e. - for each topic-SIC section combination where activity has been normalised such that the activities for each topic sum to one.
This highlights which sectors contribute most toward the activity in each topic.
For example, Other service activities has an activity of 0.54 in topic 4 meaning that 54% of topic activity in topic 4 relates to Other service activities.

### SIC division

The section level of SIC is perhaps too coarse, therefore we also explore topic activity levels at the SIC division level.

<div class=altair s3_path="scotland_div_topic_activity_level_3_norm_by_sector.json" static_path="scotland_div_topic_activity_level_3_norm_by_sector.png" id="fig:div_topic_activity_sector" height="100%">Topic activity (3rd hierarchy level) by SIC division. Topics are normalised such that the topic activity for each sector sums to 1.
</div>

Figure [@fig:div_topic_activity_sector] shows the levels of topic activity - i.e. - for each topic-SIC division combination where activity has been normalised such that the activities for each sector sum to one. This highlights which topics each sector is more likely to talk about. 


<div class=altair s3_path="scotland_div_topic_activity_level_3_norm_by_topic.json" static_path="scotland_div_topic_activity_level_3_norm_by_sector.png" id="fig:div_topic_activity_topic" height="100%">Topic activity (3rd hierarchy level) by SIC division. Topics are normalised such that the topic activity for each topic sums to 1.
</div>

Figure [@fig:div_topic_activity_topic] shows the levels of topic activity - i.e. - for each topic-SIC division combination where activity has been normalised such that the activities for each topic sum to one.
This highlights which sectors contribute most toward the activity in each topic.


### Trend

<div class=altair s3_path="topic_trend_by_section.json" static_path="topic_trend_by_section.png" id="fig:topic_trend_by_section">
Top: Activity in each topic by SIC section (y-axis) and month (colour).
Bottom: Trends in the top 5 topics for each SIC section.
</div>

Figure [@fig:topic_trend_by_section] shows the topic activity in SIC sections over time, with the bottom of the plot showing the trends in the top 5 topics for each section. Trends within sections are mostly non-existent apart from particularly evident temporal trends in Agriculture, Forestry And Fishing, and Manufacturing sections; however these trends are for the vague four dominant (and uninformative) topics. 
Performing trend analysis with only three time-points is not an ideal exercise when we do not know when in the month the notices were collected - they could have all been collected at the beginning of a month or randomly distributed throughout.

### Relation to exposure

<div class=altair s3_path="topic_corr_plot.json" static_path="topic_corr_plot.png" style="align:center" id="fig:topic_corr_plot">Left: Distribution of the correlation between topic activity in SIC sections with the google trends exposure score for that SIC section.
Right: Scatterplot of topic activity against google trends exposure for the highest and lowest correlations in the plot to the left.
</div>

[@fig:topic_corr_plot] shows the results of correlating each topic with the exposure measure of [@sec:] for the months for which the datasets overlap. The distribution of correlations fluctuates around zero with the biggest positive and negative correlations (displayed on the right of the figure) showing no real relationship.


### Exploring finer structure for insight

<div class=altair s3_path="scotland_topic_activity_level_2_norm_by_sector.json" static_path="scotland_topic_activity_level_2_norm_by_sector.png" id="fig:topic_activity_sector_2" height="100%">Topic activity (2nd hierarchy level) by SIC division. Topics are normalised such that the topic activity for each sector sums to 1.
</div>

In light of the 3rd hierarchy level containing 4 dominant topics, we briefly check the 2nd hierarchy level to explore whether there any useful finer structure is revealed. 
Figure [@fig:topic_activity_sector_2] shows the levels of topic activity - i.e. - for each topic-SIC division combination where activity has been normalised such that the activities for each sector sum to one. 
There no longer appear to be 4 dominant topics and a few more common sense features appear such as Public administration business websites talking about grants (topic ); however this level of the hierarchy is diffuse and uninformative. Furthermore, one particularly troubling feature is revealed, the topic activity for Accomodation and Food Services is zero for topic 125 which contains the top words: "delivery", "order", "shop", "store", "collection", "item", "collect", "your_order", "card", "royal_mail". The topic activity for topic 125 in Wholesale and Retail Trade businesses is only 0.02. We would expect both these sectors to be talking about this topic!

This shortcoming raised fresh questions over whether the data was of sufficient quality and whether there were features in the data that led to data not being suitable for an analysis of this type.

Are talking about 4 and 10 a bit which talks about open and closed but mixed together.

- 4: 'open; covid_19_outbreak; corona_virus; glasgow; difficult_time; forward_to; soon; we_look; to_close; open_for',
-10: 'please; safe; closed; thank_you; notice; we_would; in_line; safety_of; stay_safe; like_to',

Note: similar when looking at division level except even more sparse (and even less visible in figure)

### Manual labelling

The lack of correlation with other exposure measures and the lack of insightful results coming out of analysing topic activity at the sector level led us to label a random sample of 200 Scottish notices.
We chose to label these as "Relevant", "Irrelevant", or "Ambiguously relevant" to a businesses response to Covid-19.

| Relevant | Irrelevant | Amiguous |
| ---      | ---        | ---      |
| 96       | 82         | 22       |
: Results of hand-labelling a random sample of 200 notices from Scottish businesses with their relevance to the response of a business to Covid-19. {#tbl:notice-labels}

[@tbl:notice-labels] shows the results of this hand-labelling. Approximately 40% of notices were irrelevant to a businesses response to Covid-19, with approximately a further 10% being of ambiguous relevance - this is a strikingly large fraction of notices to not be relevant and is likely a large contributing factor for the poor outcomes of the topic modelling approach.

Notices labelled as irrelevant were typically either: 

- Not related to covid at all
- A generic statement referencing that covid is happening / repeating govt. guidance
- A truncated snippet such as "COVID-19 update"

Ambiguously relevant notices were notices that it was hard to definitively flag as relevant or not. Often these are discussing Covid-19 in the context of a business but tend to be either misssing important context; cryptic; or discussing activities of businesses such as GP's, pharmacies, cleaning businesses where the text is discussing regular activity of such businesses as much as it is discussing a response to the shocks of Covid-19.
Examples of ambiguously relevant notices are shown below, 

> A socially distanced photo shoot for Lauren and Duchess. What a lovely birthday gift from family

> COVID-19 Please note that we've updated our opening hours - these are listed at the bottom of page. We will add further updates here as we know more.

> Due to the outbreak of Coronavirus, you should NOT attend the Practice unless advised to by a Clinician. All prescriptions will be sent to a local pharmacy or posted to you, as will all fit notes and letters. For any enquiries you can email us on gg-uhb.gp49111clinical@nhs.net

> 12 May 2020 Civic Amenity Booking System by dgfarmer | posted in: Uncategorised | 0 Modus helps Civic Amenity Sites re-open after lockdown. We have been working with various Civic Amenity Site operators to produce a booking system suitable for use to regulate traffic at sites as they re-open after l...


A further factor likely contributing to the poor outcomes from the topic modelling is the distribution of notice lengths - a large number of notices are extremely short and a large number are extremely long! Figure [@fig:notice_length] shows the notice length distribution - note the logarithmic x-scale.


<!-- Histograms require too much data for interactives! -->
<!-- <div class=altair s3_path="notice_length.json" static_path="notice_length.png" id="fig:notice_length">. -->
<!-- </div> -->
![Notice length distribution](../../figures/notice_length.png){#fig:notice_length_png}

For example, the following notices are short and concise,

> COVID-19 Update: McDermid Controls are still operating during this time whilst following government guidelines. For any enquiries please contact us here

> Due to the current coronavirus situation the clinic is closed until further notice.

> The course is open. Please remember to adhere to the government social distancing 2 metre guidelines.

Whereas the next notice is extremely long (and is also several months out of date),

> COVID-19 – PRECAUTIONARY MEASURES WITHIN ICE FACTOR UPDATE 20/03/2020: We are closing temporarily We are closing temporarily at 10pm tonight (20th March 2020) as requested by the UK Government. We are continuing to comply with the guidelines they have issued and hope you will too. We apologise for the inconvenience this will cause. It is only temporary and we hope to see you later when we reopen on the other side of the outbreak. We would like to thank you for your continued custom and will be back before you know it. In the meantime, take care, stay well and look after yourself, your health and your loved ones. We will keep in touch and let you know when we are due to reopen but for now, here is some information on what to do if you have a booking and some helpful tips for isolation should it be of any help. what to do if you have made a booking + All bookings will be honoured. + We will get in touch as soon as we can to move your booking to a date that suits once we reopen. + As we will be closed we ask that you email us at info@ice-factor.co.uk if you need us. + Please only send one email, on one communication platform. We will respond to everyone as soon as we can. + When we reopen will have a backlog of emails to work through so we ask that you bear with us and be mindful of the pressure our team will be under to process everyone’s correspondence. Some helpful advice during these times We will keep this blog updated regularly to keep our customers advised and in accordance with the latest guidance issued by the Scottish Government / Health Protection Scotland. LESSONS AND ACTIVITY AREAS ICE WALL – CLOSED – CLOSED ROCK WALL – CLOSED – CLOSED AERIAL ADVENTURE COURSE – CLOSED – CLOSED CAFE – CLOSED – CLOSED CHILLERS BAR & GRILL – CLOSED WHAT WE’RE DOING In line with the latest guidance, Ice Factor has undertaken various steps to help safeguard staff and customers in the facility. On the premises, visitors will see signage reminding you to wash hands for a minimum of 20 seconds, using soap and water; particularly after coughing, sneezing and going to the bathroom. We are advised this simple practice is one of the most effective ways to help alleviate the spread of the virus. We have also installed hand sanitizer stations throughout the centre and we strongly advise our customers to use these. In addition, we have increased our Clean Team with additional focus placed on high traffic areas such as door handles, push plates and handrails. All of our staff are being kept up to date with government advice and guidelines. WHAT WE ASK YOU TO DO Everyone has a responsibility to ensure they are doing their bit to stop the spread of the virus and so, we ask all of our visitors to: Please wash your hands regularly using soap and water, the above guidelines are the official recommendations outlined by the NHS. Cover your mouth and nose with a tissue should you sneeze or cough and bin it right away. If you display symptoms of the virus or have come in to contact with someone who has the virus follow the latest guidelines issued by the NHS prior to visiting us (or any other public place). Consider the impact on yourself and others (particularly those who may be vulnerable) prior to leaving your home should you be displaying symptoms or have been in contact with someone who has symptoms/the virus/been advised to isolate. Importantly, we kindly ask those travelling from abroad or who may be most vulnerable to the risk of infection to follow the latest guidance fromHealth Protection Scotland. WE ASK YOU KINDLY BUT FIRMLY NOT TO VISIT ICE FACTOR IF YOU DISPLAY THE SYMPTOMS OUTLINED IN THE LATEST ADVICE (13 March 2020) BY HEALTH PROTECTION SCOTLAND – https://www.hps.scot.nhs.uk/ IF YOU HAVE SYMPTOMS Should you contract the virus or have been advised to self-isolate due to showing symptoms, we want to make it easy for you to move your booking with us. We are therefore happy to extend the validity of gift vouchers and waive our administration fee which is normally charged to help you take the time you need to recover. Our team can do this over the phone and will move your lesson or session to a future date that suits. Cancellations and refunds At this time we are not issuing cancellations or refunds for bookings as we are operating as normal and presently have received no advice to change this at the current time. Should this change we will update you on this page. We want to make it easier to move your booking with us. As such, we will not be able to issue a refund for any bookings made however we have waived the £5 administration fee and the 5 day notice period. Our team are here to help and will be happy to move your booking forward to a date that suits. IF YOU NEED US, WE’RE HERE Our team are available should you need to contact them on info@ice-factor.co.uk or 01855 831 100. We are experiencing a higher volume of calls at the moment so please bear with us while we respond to you as quickly as we can. Thank you The team at Ice Factor

Furthermore, relevant notices are often missing important context or contain information we couldn't interpret such as lots of notices stating new opening hours,

>  Covid-19 (Coronavirus) Opening hours: Monday to Friday 8am-5pm Saturday and Sunday - closed

Such notices are hard to algorithmically disambiguate from general statements about a business still being open or having to close due to Covid-19.

# Discussion

In summary, the exploration of business website notices using topic modelling failed to yield insights of note but did highlight data quality issues such as a large proportion of notices not being relevant to businesses responses to Covid-19 and the tendency for many notices to be extremely long and thus dillute the important information contained within a notice.
Without the investment of significant time in improving the quality of the notice data, we do not believe business website notice data is capable of statistically mapping the impact of Covid in Scotland; however, licensing and cost issues aside, the data could find value in being developed into an exploratory tool to help individual policymakers find notices relevant to their specific question be that focussing on a region, sector, or keyword.

<!-- 
> Covid-19 & EVM In light of the shortage of critical PPE Equipment in the UK, we have now introduced updated safe working practices in our factory. This will enable our key production workers to manufacture protective visors and social distancing screens for Care Homes and the NHS. Our account managers, admin team, art working and technical drawing teams are all busily working from home and connected to our IT systems, enabling them to continue working as required. Phone calls to our main number will be re-directed, so please be patient, and we will be happy to direct your call to the most appropriate person. We will be available during normal business hours as and when you need us. You can view our protection and social distancing products here 
A policymaker might want to identify companies such as this?
-->

There are two principle significant investments required to improve data quality.
Firstly, the data collected by Glass must be more reliable and complete: notices that are truncated must not be truncated; notices containing snippets from different sections of a businesses website must be separated; the time and date of collection must be provided rather than just a month. Unfortunately improved data collection would have to start again and would not be able to recover historic information, thus losing a key feature of the data.
Secondly, better processing of the notices must be performed such that irrelevant notices are filtered out and relevant notices are classified into several categories such as "Business as usual", "Temporary closure", "Permanent closure", "Adaptation", "Partial closure" etc. This would likely require hand-annotation of the relevant sections of a subset of notices; training a model on these labels; extrapolating to the rest of the notices using the model; and performing a validation study on the results.
