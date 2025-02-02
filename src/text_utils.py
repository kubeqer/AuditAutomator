from loguru import logger
from models import OpenSCAPRule, DetailItemLynis, SuggestionItemLynis


def create_text_for_openscap(rule: OpenSCAPRule) -> str:
    """
    Builds a string from the OpenSCAPRule fields.
    """
    text = f"{rule.title} {rule.description} {rule.rationale}"
    logger.debug(f"[create_text_for_openscap] {text}")
    return text


def create_text_for_detail(detail: DetailItemLynis) -> str:
    """
    Builds a string from the DetailItemLynis fields, including nested DescriptionLynis if present.
    """
    parts = []
    if detail.service:
        parts.append(detail.service)
    if detail.description:
        if detail.description.desc:
            parts.append(detail.description.desc)
        if detail.description.value:
            parts.append(detail.description.value)
        if detail.description.field:
            parts.append(detail.description.field)
        if detail.description.prefval:
            parts.append(detail.description.prefval)
    text = " ".join(parts)
    logger.debug(f"[create_text_for_detail] {text}")
    return text


def create_text_for_suggestion(sugg: SuggestionItemLynis) -> str:
    """
    Builds a string from the SuggestionItemLynis fields.
    """
    parts = [sugg.id or ""]
    if sugg.severity:
        parts.append(sugg.severity)
    if sugg.description:
        parts.append(sugg.description)
    text = " ".join(parts)
    logger.debug(f"[create_text_for_suggestion] {text}")
    return text
