from typing import List, Dict, Any, Tuple
from loguru import logger
from models import OpenSCAPRule, DetailItemLynis, SuggestionItemLynis
from text_utils import (
    create_text_for_openscap,
    create_text_for_detail,
    create_text_for_suggestion,
)
from embedding_utils import get_embedding, cosine_similarity


def compare_objects(
    openscap_rules: List[OpenSCAPRule],
    detail_items: List[DetailItemLynis],
    suggestion_items: List[SuggestionItemLynis],
) -> Dict[str, Any]:
    """
    For each OpenSCAP rule, computes the cosine similarity with every candidate from
    the combined detail and suggestion lists. The candidate with the highest similarity
    is selected. If the highest similarity exceeds 0.5, the rule and candidate are paired
    and removed from further comparisons. Otherwise, the rule is marked as unpaired.

    After processing all OpenSCAP rules, any remaining detail or suggestion items are also
    marked as unpaired.

    Returns:
        dict: {
            "pairs": List of tuples (oscap_rule, candidate, similarity, verified=True),
            "unpaired_openscap": List of OpenSCAPRule objects not paired,
            "unpaired_detail": List of DetailItemLynis objects not paired,
            "unpaired_suggestion": List of SuggestionItemLynis objects not paired
        }
    """
    logger.info("Starting pairwise comparisons.")

    osc_embeddings = [
        (rule, get_embedding(create_text_for_openscap(rule))) for rule in openscap_rules
    ]
    det_embeddings = [
        (detail, get_embedding(create_text_for_detail(detail)))
        for detail in detail_items
    ]
    sugg_embeddings = [
        (sugg, get_embedding(create_text_for_suggestion(sugg)))
        for sugg in suggestion_items
    ]

    pairs: List[Tuple[Any, Any, float, bool]] = []
    unpaired_osc: List[OpenSCAPRule] = []

    remaining_det = det_embeddings.copy()
    remaining_sugg = sugg_embeddings.copy()

    for rule, emb_rule in osc_embeddings:
        best_sim = 0.0
        best_candidate = None
        best_candidate_type = None

        for detail, emb_det in remaining_det:
            sim = cosine_similarity(emb_rule, emb_det)
            if sim > best_sim:
                best_sim = sim
                best_candidate = detail
                best_candidate_type = "detail"

        for sugg, emb_sugg in remaining_sugg:
            sim = cosine_similarity(emb_rule, emb_sugg)
            if sim > best_sim:
                best_sim = sim
                best_candidate = sugg
                best_candidate_type = "suggestion"

        if best_sim > 0.5 and best_candidate is not None:
            pairs.append((rule, best_candidate, best_sim, True))
            logger.debug(
                f"Pair found: Rule '{rule.title}' with candidate type '{best_candidate_type}' (sim={best_sim:.3f})"
            )
            if best_candidate_type == "detail":
                remaining_det = [
                    (d, emb) for (d, emb) in remaining_det if d != best_candidate
                ]
            elif best_candidate_type == "suggestion":
                remaining_sugg = [
                    (s, emb) for (s, emb) in remaining_sugg if s != best_candidate
                ]
        else:
            unpaired_osc.append(rule)
            logger.debug(
                f"No suitable pair for Rule '{rule.title}' (best sim={best_sim:.3f}). Marking as unpaired."
            )

    unpaired_det = [d for (d, emb) in remaining_det]
    unpaired_sugg = [s for (s, emb) in remaining_sugg]

    logger.info("Comparisons completed.")
    return {
        "pairs": pairs,
        "unpaired_openscap": unpaired_osc,
        "unpaired_detail": unpaired_det,
        "unpaired_suggestion": unpaired_sugg,
    }
