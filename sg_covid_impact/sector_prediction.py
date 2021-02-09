import random
import logging
import pandas as pd
import numpy as np
import altair as alt

from sklearn.preprocessing import LabelBinarizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

import sg_covid_impact
from sg_covid_impact.extract_salient_terms import make_glass_ch_merged
from sg_covid_impact.make_sic_division import (
    make_section_division_lookup,
)
from sg_covid_impact.utils.altair_save_utils import (
    google_chrome_driver_setup,
    save_altair,
)
from sg_covid_impact.utils.altair_s3 import export_chart

from sg_covid_impact.sic import load_sic_taxonomy, extract_sic_code_description

from nltk.corpus import stopwords

STOPWORDS = stopwords.words("english")

project_dir = sg_covid_impact.project_dir


def train_model(gl_sector):
    """Trains a logistic model on the Glass data"""
    logging.info(f"Training with {str(len(gl_sector_sample))}")

    # Count vectorise the descriptions
    logging.info("Pre-processing")
    # One hot encoding for labels
    # Create array of divisions
    labels = np.array(np.array(gl_sector_sample["division"]))
    # Create the features (target and corpus)
    lb = LabelBinarizer()
    lb.fit(labels)
    y = lb.transform(labels)

    # Count vectorised corpus
    corpus = list(gl_sector_sample["description"])
    count_vect = TfidfVectorizer(
        stop_words=STOPWORDS,
        ngram_range=(1, 2),
        min_df=20,
        max_df=0.1,
        max_features=10000,
    ).fit(corpus)

    X = count_vect.transform(corpus)

    logging.info(X.shape)

    # Train, test splits
    X_train, X_test, Y_train, Y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Initialise the model
    m = OneVsRestClassifier(
        LogisticRegression(C=1, class_weight="balanced", solver="liblinear")
    )

    # Train the model
    logging.info("Training")
    m.fit(X_train, Y_train)

    return lb, count_vect, X_test, Y_test, m


def validate_results_single(prob_vector, true_label, thres=0.1):
    """Compares predicted labels with actual labels for a single observation
    Args:
        prob_vector (series): sector probability vector
        true_label (str): true value of the sector
        thres (float): minimum threshold to consider that a sector has been
            classified
    """
    # Is the actual label the top predicted label?
    true_is_top = prob_vector.idxmax() == true_label

    # Is the actual label above 0.5?
    true_is_high = prob_vector[true_label] > 0.5

    # Is the actual label in the top 5 predicted labels?
    # Is the actual label in the top 5 and 10 predicted labels?
    prob_vector_sorted = prob_vector.sort_values(ascending=False).index

    true_in_top_5, true_in_top_10 = [
        true_label in prob_vector_sorted[:n] for n in [5, 10]
    ]
    # Is the actual label predicted at all (prob >thres)
    true_is_predicted = prob_vector[true_label] > thres

    # Is the predicted label in the same division as the top predicted label
    shared_section = (
        div_sect_lookup[prob_vector.idxmax()] == div_sect_lookup[true_label]
    )

    outputs = pd.Series(
        [
            true_is_top,
            true_is_high,
            true_in_top_5,
            true_in_top_10,
            true_is_predicted,
            shared_section,
        ],
        index=[
            "true_top",
            "true_high",
            "true_top_5",
            "true_top_10",
            "true_predicted",
            "same_section",
        ],
    )
    return outputs


def validate_results(pred_df, labels, thres=0.2):
    """Compares predicted labels with actual labels
    Args:
        pred_df (df): all prediction probabilities
        labels (series): labels
        thres (float): minimum threshold to consider a sector present in the predictions
    """
    out = pd.DataFrame(
        [
            validate_results_single(pred_df.iloc[n], labels[n], thres=thres)
            for n in np.arange(0, len(pred_df))
        ]
    )

    out["true_label"] = labels

    return out


def process_validation_outputs(out):
    """Process model validation so we can visualise it"""
    model_performance_by_division = (
        out.groupby("true_label")
        .mean()
        .reset_index(drop=False)
        .melt(id_vars=["true_label"], var_name="metric", value_name="share")
        .assign(section=lambda x: x["true_label"].map(div_sect_lookup))
        .assign(description=lambda x: x["true_label"].map(div_code_description))
        .assign(section_name=lambda x: x["section"].map(section_name_lookup))
    )

    sort_divs = (
        model_performance_by_division.query("metric == 'true_predicted'")
        .sort_values(["section", "share"], ascending=[True, False])["true_label"]
        .to_list()
    )

    sort_vars = ["true_top", "true_high", "true_top_5", "true_top_10"]

    model_performance_by_division_selected = model_performance_by_division.loc[
        model_performance_by_division["metric"].isin(sort_vars)
    ]

    return model_performance_by_division_selected, sort_divs


def plot_model_performance(perf, sort_divisions):
    perf_chart = (
        alt.Chart(perf)
        .mark_bar()
        .encode(
            y=alt.Y(
                "true_label",
                sort=sort_divisions,
                axis=alt.Axis(ticks=False, labels=False),
            ),
            x="share",
            color=alt.Color("section_name:O", scale=alt.Scale(scheme="category20")),
            tooltip=["true_label", "description", "share"],
            column=alt.Column("metric", sort=sort_divisions),
        )
        .resolve_scale(x="independent")
    ).properties(width=100, height=500)

    return perf_chart


if __name__ == "__main__":

    train_test_size = 300000

    div_code_description = extract_sic_code_description(load_sic_taxonomy(), "Division")
    div_sect_lookup, section_name_lookup = make_section_division_lookup()

    logging.info("Creating glass - ch dataset")
    gl_sector = make_glass_ch_merged()

    # Process and sample
    gl_sector = gl_sector.dropna(axis=0, subset=["description", "division"])

    gl_sector = gl_sector.loc[
        [len(x) > 300 for x in gl_sector["description"]]
    ].reset_index(drop=True)

    gl_sector_sample = gl_sector.loc[
        random.sample(list(np.arange(len(gl_sector))), train_test_size)
    ]

    # Train model
    lb, count_vect, X_test, Y_test, model = train_model(gl_sector_sample)

    # Validation
    test_labels = model.predict_proba(X_test)

    # How does the real label distribution relate to the test label distribution
    actuals = lb.inverse_transform(Y_test)
    preds_df = pd.DataFrame(test_labels, columns=lb.classes_)

    # Validate results
    out = validate_results(preds_df, actuals, thres=0.05)
    perf, sort_divisions = process_validation_outputs(out)

    # Visualise validation outputs
    driver = google_chrome_driver_setup()
    perf_chart = plot_model_performance(perf, sort_divisions)
    save_altair(perf_chart, "appendix_model_validation", driver=driver)
    export_chart(perf_chart, "appendix_model_validation")

    # Apply model to population of companies and save results
    X_all = count_vect.transform(gl_sector["description"])

    # This creates a df with predicted probabilities for all data in the corpus
    preds_all = pd.DataFrame(model.predict_proba(X_all), columns=lb.classes_)
    preds_all["id_organisation"] = gl_sector["org_id"]
    preds_all.to_csv(
        f"{project_dir}/data/processed/glass_companies_predicted_labels_v2.csv",
        index=False,
    )
