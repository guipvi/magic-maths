"""
Commander Cast Analysis Engine

Computes per-turn probability of casting the commander given:
- Available mana (from mana_ramp analysis)
- Minimum accumulated category events (from category_analysis)
- Mana left over after casting
"""

import numpy as np
from scipy.stats import hypergeom


def _hypergeom_cdf(N, K, n, k):
    if N <= 0 or K <= 0 or n <= 0:
        return 0.0
    if k < 0:
        return 0.0
    try:
        return hypergeom.cdf(k, N, K, n)
    except Exception:
        return 0.0


def analyze_commander_cast(deck_size, commander_cmc, mana_left_over,
                           min_category_requirements, land_count,
                           category_assignments=None, category_analysis_by_turn=None,
                           mana_ramp_by_turn=None):
    """
    deck_size: total cards in deck
    commander_cmc: commander's converted mana cost
    mana_left_over: how much mana to keep floating after casting
    min_category_requirements: [{"category_id": int, "count": int}, ...]
    land_count: number of lands in deck
    category_assignments: list of dicts with category_id per card
    category_analysis_by_turn: dict of turn -> {categories: {cat_id: {total_expected, prob_at_least_1, ...}}}
    mana_ramp_by_turn: dict of turn -> {total_expected_mana, mana_from_lands, ramp_contributions}

    Returns: dict with per-turn analysis
    """
    required_mana = commander_cmc + mana_left_over
    total_cards_in_deck = deck_size

    # Count cards per category for hypergeometric
    cat_counts = {}
    if category_assignments:
        for a in category_assignments:
            cid = a['category_id']
            cat_counts[cid] = cat_counts.get(cid, 0) + 1

    results = {}
    for turn in range(1, 11):
        n_drawn = min(7 + (turn - 1), total_cards_in_deck)

        # Mana probability
        mana_info = None
        if mana_ramp_by_turn and turn in mana_ramp_by_turn:
            total_mana = mana_ramp_by_turn[turn].get('total_expected_mana', 0)
            mana_info = {
                'total_expected_mana': total_mana,
                'enough_mana': bool(total_mana >= required_mana),
                'mana_after_cast': int(max(0, total_mana - commander_cmc)) if total_mana >= commander_cmc else 0,
            }

        # Category requirement probabilities
        category_results = []
        all_met = True
        for req in min_category_requirements:
            cid = req['category_id']
            req_count = req['count']
            cat_count = cat_counts.get(cid, 0)

            prob = 0.0
            pool_expected = 0.0

            if category_analysis_by_turn and turn in category_analysis_by_turn:
                cat_entry = category_analysis_by_turn[turn].get('categories', {}).get(cid, {})
                pool_expected = cat_entry.get('total_expected', 0)
                if req_count == 1:
                    prob = cat_entry.get('prob_at_least_1', 0.0)
                elif req_count == 2:
                    prob = cat_entry.get('prob_at_least_2', 0.0)
                elif req_count == 3:
                    prob = cat_entry.get('prob_at_least_3', 0.0)

            meets_req = bool(pool_expected >= req_count)
            if not meets_req:
                all_met = False

            category_results.append({
                'category_id': cid,
                'required': req_count,
                'expected_pool': round(pool_expected, 2),
                'prob_met': round(prob, 4),
                'is_met_expected': meets_req,
            })

        combined_prob = 0.0
        if mana_info and mana_info['enough_mana'] and all_met:
            # Rough joint probability: use the min of all condition probabilities
            probs = [mana_info.get('prob_enough_mana', 1.0)]
            for cr in category_results:
                if cr['required'] > 0:
                    probs.append(cr['prob_met'] if cr['prob_met'] > 0 else 0.5)
            combined_prob = round(min(probs), 4) if probs else 0.0

        results[turn] = {
            'turn': turn,
            'cards_drawn': n_drawn,
            'required_mana': required_mana,
            'mana': mana_info,
            'category_requirements': category_results,
            'all_category_requirements_met_expected': all_met,
            'combined_probability': combined_prob,
        }

    return {
        'commander_cmc': commander_cmc,
        'mana_left_over': mana_left_over,
        'required_mana': required_mana,
        'min_category_requirements': min_category_requirements,
        'by_turn': results,
    }
