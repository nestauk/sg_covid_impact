import gtab
import pandas as pd
import logging
import re
import yaml
import sg_covid_impact

project_dir = sg_covid_impact.project_dir

# https://github.com/epfl-dlab/GoogleTrendsAnchorBank


def get_all_results(div_dataset, t, threshold=0.1):
    """Obtains google search results for all terms related to all SIC divisions
    Args:
        div_dataset: df with divisions, keywords and their salience
        t: gtab object
        threshold: salience threshold for including a query
    """
    for div in set(div_dataset["division"]):
        df = div_dataset.query(f"division == '{div}'")
        sel = df.loc[df["salience"] >= threshold]["keyword"].tolist()

        if len(sel) > 0:  # Sometimes there aren't any terms above the threshold
            logging.info(f"Getting division {div}")
            div_df = get_div_results(sel, t, threshold)

            div_df["division"] = div
        else:
            logging.info(f"No salient terms for division {div}")

    return div_df


def get_div_results(sel, t):
    """Queries google trends with a list of keywords
    Args:
        sel: list of keywords
        t: gtab object
    Returns:
        a df with search volumes
    """

    div_list = []
    columns = []
    for word in sel:
        word_clean = re.sub("_", " ", word)  # Remove underscores
        try:
            trend = t.new_query(word_clean)["max_ratio"]
            div_list.append(trend)
            columns.append(word_clean)
        except Exception as e:  # Some keywords return an error
            print(e)

    div_df = pd.concat(div_list, axis=1)
    div_df.columns = columns

    return div_df


def make_div_trend_data():
    # Model config
    with open(project_dir / "/sg_covid_impact/model_config.yaml", "rt") as f:
        config = yaml.safe_load(f.read())["google_search"]

    term_salience = config["term_salience_threshold"]

    # This is a placeholder to be updated when I port the rest of the
    # Pipeline here.
    salient_word_df = pd.read_csv(f"{project_dir}/data/aux/division_term_freqs.csv")

    # Initialise the gtab
    t = gtab.GTAB()

    # Container to store results
    all_trends = []

    for v in config["anchor_periods"].values():
        # Creates an anchorbank and collects data for 2020 and 2019
        logging.info(f"Making anchorbank for period {v}")

        year = v.split("-")[0]

        t.set_options(pytrends_config={"geo": "GB", "timeframe": v})
        t.create_anchorbank()

        logging.info(f"Extracting trends for period {v}")
        t.set_active_gtab(f"google_anchorbank_geo=GB_timeframe={v}.tsv")
        trend_period = get_all_results(salient_word_df, t, term_salience)
        trend_period["year"] = year
        all_trends.append(trend_period)

    logging.info("Saving results")
    all_trends_df = pd.concat(all_trends)

    all_trends_df.to_csv(f"{project_dir}/data/processed/term_search_trends_{year}.csv")


if __name__ == "__main__":
    make_div_trend_data()
