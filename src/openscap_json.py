import json
from typing import List
from loguru import logger
from models import OpenSCAPRule
from consts import OPENSCAP_REPORT


def load_openscap_rules() -> List[OpenSCAPRule]:
    """
    Converts the 'rules' JSON dictionary into a list of validated OpenSCAPRule objects,
    using Pydantic for data validation and Loguru for logging.

    Args:
        rules_json (dict): Dictionary read from the "rules" key in the OpenSCAP JSON report.

    Returns:
        List[OpenSCAPRule]: A list of OpenSCAPRule objects with validated fields.
    """

    with open(OPENSCAP_REPORT, "r") as file:
        openscap_report = json.load(file)
    rules = openscap_report.get("rules", {})
    rules_list = list(rules.values())

    logger.info(f"Found {len(rules_list)} rules in JSON. Parsing now.")

    parsed_rules = []
    for idx, rule_dict in enumerate(rules_list, start=1):
        rule_obj = OpenSCAPRule(**rule_dict)
        parsed_rules.append(rule_obj)
        logger.debug(f"[{idx}] Parsed rule: {rule_obj.title}")

    logger.info(f"Successfully parsed {len(parsed_rules)} rules.")
    return parsed_rules
