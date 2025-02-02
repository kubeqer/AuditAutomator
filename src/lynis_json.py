import json
from loguru import logger

from consts import LYNIS_REPORT
from models import SuggestionItemLynis, DetailItemLynis


def parse_lynis_report_pydantic():
    """
    Loads the JSON and uses Pydantic to parse and validate items in details[] and suggestion[].
    Returns a list of DetailItemLynis objects and a list of SuggestionItemLynis objects.
    """
    logger.info(f"Loading JSON from {LYNIS_REPORT}.")
    with open(LYNIS_REPORT, "r") as f:
        data = json.load(f)

    details_list = data.get("details[]", [])
    suggestions_list = data.get("suggestion[]", [])

    logger.info(
        f"Found {len(details_list)} details and {len(suggestions_list)} suggestions in the JSON file."
    )

    logger.debug("Parsing details with Pydantic.")
    parsed_details = [DetailItemLynis(**item) for item in details_list]

    logger.debug("Parsing suggestions with Pydantic.")
    parsed_suggestions = [SuggestionItemLynis(**item) for item in suggestions_list]

    logger.info(
        f"Successfully parsed {len(parsed_details)} DetailItemLynis objects and {len(parsed_suggestions)} SuggestionItemLynis objects."
    )

    return parsed_details, parsed_suggestions
