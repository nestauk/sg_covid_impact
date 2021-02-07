# %%
"""Queries relating to geographical queries."""
from sg_covid_impact.utils.metaflow import cache_getter_fn
from sg_covid_impact.getters.glass import GETTER, get_notice
from sg_covid_impact.getters.nspl import get_nspl


@cache_getter_fn
def get_scottish_address_ids() -> set:
    """Glass `address_id`'s located in Scotland.

    TODO: augment with CH data
    """
    return (
        GETTER.address.merge(
            get_nspl()[["pcds", "laua"]].dropna().rename(columns={"pcds": "postcode"}),
            on="postcode",
        )
        .loc[lambda x: x.laua.str.startswith("S"), "address_id"]
        .pipe(set)
    )


@cache_getter_fn
def get_organisation_ids_for_scotland() -> set:
    """Glass `organisation_id`'s located in Scotland."""

    scottish_address_ids = get_scottish_address_ids()
    return GETTER.organisationaddress.loc[
        lambda x: x.address_id.isin(scottish_address_ids), "org_id"
    ].pipe(set)


@cache_getter_fn
def get_notices_for_scotland() -> set:
    """Glass notices for organisations in Scotland."""
    organisation_ids = get_organisation_ids_for_scotland()
    return get_notice().loc[lambda x: x.org_id.isin(organisation_ids)]


@cache_getter_fn
def get_notice_ids_for_scotland() -> set:
    """Glass `notice_id`'s for organisations in Scotland."""
    return get_notices_for_scotland().notice_id.pipe(set)
