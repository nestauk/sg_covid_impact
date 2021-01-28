import pandas as pd
import numpy as np
import altair as alt
from itertools import combinations
import networkx as nx
import sg_covid_impact
from sg_covid_impact.make_sic_division import extract_sic_code_description
from sg_covid_impact.descriptive import load_sic_taxonomy, get_date_label
from sg_covid_impact.altair_network import plot_altair_network

project_dir = sg_covid_impact.project_dir

_DIVISION_NAME_LOOKUP = extract_sic_code_description(load_sic_taxonomy(), "Division")

# Provisional function - will eventually be imported from list_utils
def flatten_list(_list):
    """Flatten a nested list"""
    return [x for el in _list for x in el]


def make_month_range(first, last):
    """Creates a list of month dates"""
    return [
        str(x).split(" ")[0][:-2] + "01" for x in pd.date_range(first, last, freq="M")
    ]


def month_string_from_datetime(dt):
    """Converts a datetime into a string with month, year and day"""
    return str(dt).split(" ")[0]


def load_predicted():
    return pd.read_csv(
        f"{project_dir}/data/processed/glass_companies_predicted_labels_v2.csv"
    )


def extract_sectors(pred_df, thres):
    """Extracts labels for sectors above a threshold
    Args:
        pred_df (df): predicted sector
        thres (float): probability threshold
    """

    long_df = (
        pred_df.reset_index(drop=False)
        .melt(id_vars="index", var_name="division", value_name="probability")
        .query(f"probability > {thres}")
    )

    out = long_df.groupby("index")["division"].apply(lambda x: list(x))

    return out


def extract_network(_list):
    """Extracts a network from a co-occurrence list"""

    edge_list = pd.Series(
        flatten_list(
            [
                ["_".join(sorted(tup)) for tup in combinations(co_occ, 2)]
                for co_occ in _list
            ]
        )
    ).value_counts()

    edge_df = edge_list.reset_index(name="weight")

    for n in [0, 1]:
        edge_df[f"e_{str(n)}"] = [
            r["index"].split("_")[n] for _id, r in edge_df.iterrows()
        ]

    edge_df.drop("index", axis=1, inplace=True)

    n = nx.from_pandas_edgelist(edge_df, source="e_0", target="e_1", edge_attr="weight")

    return n


def make_sector_space_base(sector_space, extra_edges=100):
    """Creates the base for a sector space network
    Args:
        sector_space (network): nx network object
        extra_edges (int): extra edges to add to the maximum spanning tree
    """

    max_tree = nx.maximum_spanning_tree(sector_space)

    top_edges_net = nx.Graph(
        [
            x
            for x in sorted(
                sector_space.edges(data=True),
                key=lambda x: x[2]["weight"],
                reverse=True,
            )
            if (x[0], x[1]) not in list(max_tree.edges())
        ][:extra_edges]
    )
    united_graph = nx.Graph(
        list(max_tree.edges(data=True)) + list(top_edges_net.edges(data=True))
    )

    pos = nx.kamada_kawai_layout(united_graph, dim=2)

    labs = {k: k for k, v in pos.items()}

    return pos, united_graph, labs


# Diversification options based on network structure
def make_diversification_options(network, exposure_ranking, month, exposed, safe):
    """Extracts minimum and mean distances of negatively exposed sectors
    to neutrally or positively exposed sectors
    Args:
        network (networkx): processed network
        exposure_ranking (dict): lookup between division, month and exposure
        month (int): month
        exposed (list): high exposure rankings
        safe (list): low exposure rankings
    """
    division_exposure_month = {
        k[0]: v for k, v in exposure_ranking.items() if k[1] == month
    }

    # Extract negatively and positively exposed sectors
    exposed_divs, safe_divs = [
        [k for k, v in division_exposure_month.items() if v in sectors]
        for sectors in [exposed, safe]
    ]

    # Loop over first sets and calculate distances to second set
    d = {}
    for e in exposed_divs:
        dists = []
        for s in safe_divs:
            length = nx.shortest_path_length(network, e, s)
            dists.append(length)

        d[e] = {"mean": np.mean(dists), "min": min(dists)}

    df = pd.DataFrame(d).T.reset_index(drop=False).rename(columns={"index": "division"})
    return df


def make_neighbor_shares(network, exposure_ranking, month):
    """Extracts the number of neighbors and their exposure for a sector
    Args:
        network (networkx): network object
        exposure_ranking (dict): lookup between division, month and exposure
        month: month to focus on
    """

    division_exposure_month = {
        k[0]: v for k, v in exposure_ranking.items() if k[1] == month
    }

    neighb = []
    neighb_n = {}

    for x in network.nodes:
        neighbors = list(nx.neighbors(network, x))

        neighbor_exposures = pd.Series(
            [division_exposure_month[n] for n in neighbors], name=x
        ).value_counts(normalize=True)
        neighb.append(neighbor_exposures)
        neighb_n[x] = len(list(neighbors))

    exposure_sorted = (
        pd.Series(division_exposure_month).sort_values(ascending=False).index.tolist()
    )

    df = pd.DataFrame(neighb)
    df["neighbour_n"] = df.index.map(neighb_n)

    return df.loc[exposure_sorted].fillna(0)


def plot_exposure_neighbours(neighb_shares):
    """Plots exposure of neighbours and number of neighbours by node"""

    neighb_shares_long = (
        neighb_shares.reset_index(drop=False)
        .melt(id_vars=["index", "neighbour_n"])
        .assign(division_name=lambda x: x["index"].map(_DIVISION_NAME_LOOKUP))
    )

    base = alt.Chart(neighb_shares_long).encode(
        y=alt.Y(
            "index",
            sort=neighb_shares.index.tolist(),
            axis=alt.Axis(labels=False, ticks=False),
            title="Section",
        )
    )
    ch = (
        base.mark_bar(stroke="grey", strokeWidth=0.1).encode(
            x=alt.X("value", title="Share of neighbours"),
            tooltip=["division_name"],
            color=alt.Color(
                "variable",
                scale=alt.Scale(scheme="spectral"),
                sort="descending",
                title="Exposure Ranking",
                legend=alt.Legend(orient="bottom"),
            ),
        )
    ).properties(height=400, width=200)

    bar = (
        base.mark_bar().encode(
            x=alt.X("neighbour_n", title="Number of neighbours"),
            tooltip=["division_name"],
            color=alt.Color("neighbour_n", legend=None),
        )
    ).properties(height=400, width=200)

    out = alt.hconcat(ch, bar).resolve_scale(color="independent", y="shared")
    return out


def make_national_network(p, exposures_ranked, bres, g, month="2021-01-01", **kwargs):
    """Plot"""
    ranked_dict = (
        exposures_ranked.query(f"month_year=='{month}'")
        .set_index("division")["rank"]
        .to_dict()
    )
    size_dict = bres.groupby("division")["value"].sum().to_dict()
    node_df = (
        pd.DataFrame(p)
        .T.reset_index()
        .rename(columns={0: "x", 1: "y", "index": "node"})
        .assign(node_name=lambda x: x["node"].map(_DIVISION_NAME_LOOKUP))
        .assign(node_color=lambda x: x["node"].map(ranked_dict))
        .assign(node_size=lambda x: x["node"].map(size_dict))
    )
    ch = plot_altair_network(
        node_df,
        g,
        node_label="node_name",
        node_size="node_size",
        node_color="node_color",
        **kwargs,
    )
    return ch


def make_local_network(
    p, place, exposures_ranked, bres, g, month="2021-01-01", **kwargs
):
    ranked_dict = (
        exposures_ranked.query(f"month_year=='{month}'")
        .set_index("division")["rank"]
        .to_dict()
    )
    size_dict = (
        bres.query(f"geo_nm=='{place}'")
        .groupby("division")["value"]
        .sum()
        .reset_index(drop=False)
        .assign(share=lambda x: x["value"] / x["value"].sum())
        .set_index("division")["share"]
        .to_dict()
    )
    node_df = (
        pd.DataFrame(p)
        .T.reset_index()
        .rename(columns={0: "x", 1: "y", "index": "node"})
        .assign(node_name=lambda x: x["node"].map(_DIVISION_NAME_LOOKUP))
        .assign(node_color=lambda x: x["node"].map(ranked_dict))
        .assign(node_size=lambda x: x["node"].map(size_dict))
    )
    ch = plot_altair_network(
        node_df,
        g,
        node_label="node_name",
        node_size="node_size",
        node_color="node_color",
        **kwargs,
    )
    return ch.properties(title=", ".join([place, get_date_label(month)]))
