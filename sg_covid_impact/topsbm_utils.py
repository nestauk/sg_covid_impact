from typing import Dict, Tuple, List

import altair as alt
import pandas as pd
import toolz.curried as t


def get_top_words(topics: Dict[int, Tuple[str, int]]) -> Dict[int, str]:
    """Get top words for each topic and concatenate them."""
    return {k: t.pipe(v, t.map(t.first), "; ".join) for k, v in topics.items()}


def number_topics_and_clusters(model, level: int) -> Dict[str, int]:
    """Get the number of topics and clusters for a level of the model hierarchy."""
    model.get_groups(level)
    return {
        "n_topics": model.groups[level]["Bw"],
        "n_clusters": model.groups[level]["Bd"],
    }


def get_topicdist(model, titles: List[str], level: int) -> pd.DataFrame:
    model.get_groups(level)
    return (
        pd.DataFrame(model.groups[level]["p_tw_d"].T)
        .assign(titles=titles)
        .set_index("titles")
    )


def plot_topic_activity_heatmap(topic_activity, top_words=None):
    """."""
    if top_words is None:
        top_words = {
            k: "Top words not available" for k in range(topic_activity.shape[1])
        }

    topic_activity_ = (
        topic_activity.T.reset_index()
        .assign(top_words=top_words.values())
        .melt(id_vars=["index", "top_words"])
        .assign(sector_name=lambda x: x.sector_name.str.replace("_", " ").str.title())
        .rename(
            columns={
                "index": "Topic",
                "sector_name": "Sector name",
                "value": "Activity",
                "top_words": "Top words",
            }
        )
    )

    return (
        alt.Chart(topic_activity_)
        .encode(
            x="Topic:N",
            y="Sector name:N",
            color="Activity:Q",
            tooltip=["Sector name", "Topic", "Activity", "Top words"],
        )
        .mark_rect()
        .interactive()
        .properties(width=800)
    )


def normalise_activity_by_sector(topic_activity, sector_labels):
    """Normalise s.t. each sector sums to 1."""

    norm_factor = sector_labels.dropna().groupby("sector_name").size()

    return topic_activity.divide(norm_factor, axis="rows")


def normalise_activity_by_topic(topic_activity):
    """Each topic sums to 1."""
    return topic_activity.pipe(lambda x: x / x.sum())


def normalise_activity_by_sector_month(
    topic_activity, sector_month_labels, sector_variable="sector"
):
    """Normalise s.t. each [sector, month] sums to 1."""

    norm_factor = (
        sector_month_labels.dropna()
        .groupby(
            [
                "month",
                sector_variable,
            ]
        )
        .size()
        .sort_index()
    )

    # Each sector sums to 1
    return topic_activity.reorder_levels(["month", sector_variable]).divide(
        norm_factor.reorder_levels(["month", sector_variable]), axis="rows"
    )
