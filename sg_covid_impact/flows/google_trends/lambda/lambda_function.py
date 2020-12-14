# %%
from pytrends.request import TrendReq


def lambda_handler(event, context):
    """Lambda function to query pytrends.

    Args:
        event (dict):
        context (LambdaContext): Context object - provides information about
            invocation, function, and environment.
            See https://docs.aws.amazon.com/lambda/latest/dg/python-context.html

    Returns:
        dict
    """
    pytrends = TrendReq(**event["connection_config"])
    pytrends.build_payload(event["query_terms"], **event["payload_config"])
    return pytrends.interest_over_time().to_dict(orient="records")


if __name__ == "__main__":
    event = {
        "query_terms": ["poppadoms", "bread"],
        "connection_config": {},
        "payload_config": {},
    }
    print(lambda_handler(event, None))
