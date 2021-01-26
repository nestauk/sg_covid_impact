# %%
import logging

import numpy as np
import pandas as pd
import scipy.stats as ss
from scipy.linalg import eig
from numba import jit

import sg_covid_impact

# from mi_scotland.utils.pandas import preview

logger = logging.getLogger(__name__)
np.seterr(all="raise")  # Raise errors on floating point errors


def process_complexity(df, dataset, year, geo_type, cluster, PCI=False):
    """Calculate complexity variables aggregated over the columns.

    Calculates: size, complexity index, complexity outlook index

    Args:
        df (pandas.DataFrame): Long dataframe
            Expected columns: `{"geo_nm", "geo_cd", cluster, "value"}`
        year (str): Year
        dataset (str): Name of dataset
        geo_type (str): Type of regional geography
        cluster (str): Name of cluster  column to use to pivot on
        PCI (bool, optional): If True, calculate product complexity by
            transposing input
        # TODO refactor outside of function

    Returns:
        pandas.DataFrame
    """

    X = (
        df.pipe(pivot_area_cluster, cluster).fillna(0)
        # Transpose if PCI
        .pipe(lambda x: x.T if PCI else x)
    )
    X.index.name = "cluster"

    size = X.sum(1).to_frame("size")
    complexity = (
        X.pipe(create_lq, binary=True)
        .pipe(calc_eci, sign_correction=X.sum(1))
        .pipe(lambda x: x.rename(columns={"eci": "pci"}) if PCI else x)
    )
    outlook = X.pipe(complexity_outlook_index).to_frame("coi" if not PCI else "poi")

    return (
        size.join(complexity)
        .join(outlook)
        .assign(year=year, geo_type=geo_type, source=dataset, cluster_type=cluster)
    )


def _melt_keep_index(df, value_name="value"):
    """ Fully melt a dataframe keeping index, setting new index as all but `value` """
    id_vars = df.index.names
    return (
        df.reset_index()
        .melt(id_vars=id_vars, value_name=value_name)
        .set_index([*id_vars, df.columns.name])
    )


def process_complexity_unit(df, dataset, year, geo_type, cluster):
    """Calculate unaggregated complexity analysis variables

    Calculates: raw value, location quotient, RCA?, distance, opportunity outlook gain

    Args:
        df (pandas.DataFrame): Long dataframe
            Expected columns: `{"geo_nm", "geo_cd", cluster, "value"}`
        year (str): Year
        dataset (str): Name of dataset
        geo_type (str): Type of regional geography
        cluster (str): Name of cluster  column to use to pivot on

    Returns:
        pandas.DataFrame
    """

    X = df.pipe(pivot_area_cluster, cluster).fillna(0)
    X.columns.name = "cluster"

    # Index: year, location, cluster, geo_type
    # value, LQ, RCA?, distance, OOG
    value = X.pipe(_melt_keep_index, "value")
    lq = X.pipe(create_lq).pipe(_melt_keep_index, "lq")
    has_rca = (lq > 1).rename(columns={"lq": "has_rca"})
    d = X.pipe(distance).pipe(_melt_keep_index, "distance")
    omega = 1 - X.pipe(proximity_density).pipe(_melt_keep_index, "omega")
    oog = opportunity_outlook_gain(X).pipe(_melt_keep_index, "oog")

    return (
        pd.concat([value, lq, has_rca, d, omega, oog], axis=1)
        .assign(year=year, geo_type=geo_type, source=dataset, cluster_type=cluster)
        .pipe(preview)
    )


@jit(nopython=True)
def _proximity_matrix(M):
    """ `proximity_matrix` helper function """

    n_c, n_p = M.shape
    phi = np.empty((n_p, n_p), dtype=np.float64)
    k = M.sum(0)  # Ubiquity
    for i in range(n_p):
        Mci = M[:, i]
        for j in range(n_p):
            if j > i:
                continue
            Mcj = M[:, j]
            m = max([k[i], k[j]])
            if m == 0:
                v = np.nan
            else:
                v = (Mci * Mcj).sum() / m
            phi[i, j] = v
            phi[j, i] = v
    return phi


def proximity_matrix(X, threshold=1):
    """ Calculates proximity matrix

    Proximity between entries calculates the probability that given a revealed
    comparative advantage (RCA) in entity `j`, a location also has a RCA in
    entity `i`.
    The same probability is calculated with `i` and `j` permuted, and the
    minimum of the two probabilities is then taken.

    .. math::
        \\large{ \\phi_{ij} = \\min\\left\\{\\mathbb{P}(\\text{RCA}_i \\geq 1 |
            \\text{RCA}_j \\geq 1), \\mathbb{P}(\\text{RCA}_j \\geq 1 |
            \\text{RCA}_i \\geq 1)\\right\\} } \\\\
        \\large{ \\phi_{ij} = \\frac{\\sum_c M_{ci} * M_{cj}}{\\max(k_i, k_j)} }
        k = \\sum_i M_{i, j}

    Args:
        X (pandas.DataFrame): Activity matrix [m x n]
        threshold (float, optional): Binarisation threshold for location quotient.

    Returns:
        pandas.DataFrame [n x n]
    """
    M = create_lq(X, binary=True, threshold=threshold)
    return pd.DataFrame(_proximity_matrix(M.values), index=M.columns, columns=M.columns)


def proximity_density(X, threshold=1):
    """Calculate proximity density

    .. math:
        \\omega_{ik} = \\frac{ \\sum_j M_{ij} \\phi_{jk}}{\\sum_j \\phi_{jk}}

    Args:
        X (pandas.DataFrame): Activity matrix [m x n]
        threshold (float, optional): Binarisation threshold for location quotient.

    Returns:
        pandas.DataFrame [m x n]
    """
    M = create_lq(X, binary=True, threshold=threshold)
    phi = proximity_matrix(X, threshold)
    return (M @ phi) / phi.sum(axis=0)


def distance(X, threshold=1):
    """Distance: 1 - proximity density w/ existing capabilities as NaN

    Args:
        X (pandas.DataFrame): [locations x activities]
        threshold (float, optional): Binarisation threshold for location
            quotient.

    Returns:
        pandas.DataFrame [locations x activites]
    """

    M = create_lq(X, threshold, binary=True)
    phi = proximity_matrix(X, threshold)
    return (((1 - M) @ phi) / phi.sum(axis=1)) * M.applymap(
        lambda x: np.nan if x == 1 else 1
    )


def complexity_outlook_index(X, threshold=1):
    """Calculate economic complexity outlook index

    Args:
        X (pandas.DataFrame): [locations x activities]
        threshold (float, optional): Binarisation threshold for location
            quotient.

    Returns:
        pandas.Series [locations]
    """
    M = create_lq(X, threshold, binary=True)
    d = distance(X, threshold)
    PCI = calc_eci(M.T, sign_correction=X.sum(0))

    if PCI.shape[0] != M.shape[1]:
        M = M.loc[:, PCI.index]
        d = d.loc[:, PCI.index]

    return ((1 - d) * (1 - M) * PCI.values.T).sum(axis=1)


def opportunity_outlook_gain(X, threshold=1):
    """Calculate opportunity outlook gain

    Value for existing capabilities is NaN.

    Args:
        X (pandas.DataFrame): [locations x activities]
        threshold (float, optional): Binarisation threshold for location
            quotient.

    Returns:
        pandas.DataFrame [locations x activites]
    """
    M = create_lq(X, threshold, binary=True)
    phi = proximity_matrix(X, threshold)
    d = distance(X, threshold)
    PCI = calc_eci(M.T, sign_correction=X.sum(0))

    if PCI.shape[0] != M.shape[1]:
        M = M.loc[:, PCI.index]
        phi = phi.loc[PCI.index, PCI.index]
        d = d.loc[:, PCI.index]

    return (
        (1 - M) * PCI.values.T @ (phi / phi.sum(0)) - ((1 - d) * PCI.values.T)
    ) * M.applymap(lambda x: np.nan if x == 1 else 1)


def pivot_area_cluster(df, cluster, aggfunc=sum):
    """Convert long data into a matrix, pivoting on `cluster`

    For example, take BRES/IDBR data at Local authority (LAD) geographic level
    and SIC4 sectoral level to create matrix with elements representing the
    activity level for a given LAD-SIC4 combination.

    Args:
        df (pandas.DataFrame): Long dataframe
            Expected Columns: `{"geo_nm", "geo_cd", cluster}`
        cluster (str): Column of the sector type to pivot on
        agg_func (function, optional): Aggregation function passed to
            `pandas.DataFrame.pivot_table`.

    Returns:
        pandas.DataFrame: [number areas x number cluster]

    Note: Fills missing values with zero
    """
    return (
        df
        # Fill missing values with zeros
        .fillna(0)
        # Pivot to [areas x sectors]
        .pivot_table(
            index=["geo_cd", "geo_nm"],
            columns=cluster,
            values="value",
            fill_value=0,
            aggfunc=aggfunc,
        )
    )


def create_lq(X, threshold=1, binary=False):
    """Calculate the location quotient.

    Divides the share of activity in a location by the share of activity in
    the UK total.

    Args:
        X (pandas.DataFrame): Rows are locations, columns are sectors,
        threshold (float, optional): Binarisation threshold.
        binary (bool, optional): If True, binarise matrix at `threshold`.
            and values are activity in a given sector at a location.

    Returns:
        pandas.DataFrame

    #UTILS
    """

    Xm = X.values
    with np.errstate(invalid="ignore"):  # Accounted for divide by zero
        X = pd.DataFrame(
            (Xm * Xm.sum()) / (Xm.sum(1)[:, np.newaxis] * Xm.sum(0)),
            index=X.index,
            columns=X.columns,
        ).fillna(0)

    return (X > threshold).astype(float) if binary else X


def calc_fitness(X, n_iters):
    """Calculate the fitness metric of economic complexity

    Args:
        X (pandas.DataFrame): Rows are locations, columns are sectors,
            and values are activity in a given sector at a location.
        n_iters (int): Number of iterations to calculate fitness for

    Returns:
        pandas.DataFrame

    #UTILS
    """

    X = _drop_zero_rows_cols(X)
    x = np.ones(X.shape[0])

    for n in range(1, n_iters):
        x = (X.values / (X.values / x[:, np.newaxis]).sum(0)).sum(1)
        x = x / x.mean()

    return pd.DataFrame(np.log(x), index=X.index, columns=["fitness"])


def calc_fit_plus(X, n_iters, correction=True):
    """Calculate the fitness+ (ECI+) metric of economic complexity

    Args:
        X (pandas.Dataframe): Rows are locations, columns are sectors,
            and values are activity in a given sector at a location.
        n_iters (int): Number of iterations to calculate fitness for
        correction (bool, optional): If true, apply logarithmic correction.

    Returns:
        pandas.Dataframe

    #UTILS
    """

    X = _drop_zero_rows_cols(X)

    if X.dtypes[0] == bool:
        norm_mean = np.mean
    else:
        norm_mean = ss.gmean
    x = X.values.sum(axis=1)
    x = x / norm_mean(x)

    for n in range(1, n_iters):
        x = (X.values / (X.values / x[:, np.newaxis]).sum(0)).sum(1)
        x = x / norm_mean(x)

    if correction:
        x = np.log(x) - np.log((X / X.sum(0)).sum(1))
    else:
        pass  # x = np.log(x)

    return pd.DataFrame(x, index=X.index, columns=["fit_p"])


def calc_eci(X, sign_correction=None):
    """Calculate the original economic complexity index (ECI).

    Args:
        X (pandas.DataFrame): Rows are locations, columns are sectors,
            and values are activity in a given sector at a location.
        sign_correction (pd.Series, optional): Array to correlate with ECI
            to calculate sign correction. Typically, ubiquity. If None, uses
            the sum over columns of the input data.

    Returns:
        pandas.DataFrame

    #UTILS
    """

    X = _drop_zero_rows_cols(X)

    C = np.diag(1 / X.sum(1))  # Diagonal entries k_C
    P = np.diag(1 / X.sum(0))  # Diagonal entries k_P
    H = C @ X.values @ P @ X.T.values
    w, v = eig(H, left=False, right=True)

    eci = pd.DataFrame(v[:, 1].real, index=X.index, columns=["eci"])

    # Positively correlate `sign_correction` (some proxy for diversity) w/ ECI
    if sign_correction is None:
        sign_correction = X.sum(1)
    else:
        sign_correction = sign_correction.loc[X.index]
    sign = np.sign(np.corrcoef(sign_correction, eci.eci.values)[0, 1])
    logger.info(f"CI sign: {sign}")

    return (eci - eci.mean()) / eci.std() * sign


def _drop_zero_rows_cols(X):
    """Drop regions/entities with no activity

    Fully zero column/row means ECI cannot be calculated
    """

    nz_rows = X.sum(1) > 0
    has_zero_rows = nz_rows.sum() != X.shape[0]
    if has_zero_rows:
        logger.warning(f"Dropping all zero rows: {X.loc[~nz_rows].index.values}")
        X = X.loc[nz_rows]
    nz_cols = X.sum(0) > 0
    has_zero_cols = nz_cols.sum() != X.shape[1]
    if has_zero_cols:
        logger.warning(f"Dropping all zero cols: {X.loc[:, ~nz_cols].columns.values}")
        X = X.loc[:, nz_cols]

    return X


def simple_diversity(X):
    """Generate two simple measures of diversity

    The first measure is the number of areas engaging in an activity
    The second measure is the number of areas with a revealed comparative advantage

    Args:
        X (pandas.DataFrame): Rows are locations, columns are sectors,
            and values are activity in a given sector at a location.

    Returns:
        pandas.DataFrame

    #UTILS
    """

    div_1 = X.pipe(lambda x: np.sum(x > 0, axis=1)).to_frame("div_n_active")
    div_2 = (
        X.pipe(create_lq, binary=True, threshold=1).sum(axis=1).to_frame("div_n_RCA")
    )
    return pd.concat([div_1, div_2], axis=1)
