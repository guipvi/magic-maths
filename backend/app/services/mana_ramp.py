"""
Mana Ramp Prediction Engine

Predicts available mana per turn using the category-based resource pool model.
Uses analyze_categories() which considers manually assigned categories
(ramp, draw, alcance) and card/category triggers.
For ramp categories: total_expected events mana_amount = mana contributed
Land mana computed via hypergeometric distribution.

No regex heuristics are used. If no categories/assignments exist,
returns a basic result with only land_count and avg_cmc.
"""

import numpy as np
from scipy.stats import hypergeom


def _is_land(card):
    tl = card.get('type_line', '')
    if not tl:
        return False
    return 'land' in tl.lower()


def _hypergeom_prob(n_deck, n_success, n_draw, k):
    if n_deck <= 0 or n_success <= 0 or n_draw <= 0:
        return 0.0
    if n_success > n_deck:
        n_success = n_deck
    if k > n_draw:
        return 0.0
    if k > n_success:
        return 0.0
    try:
        return hypergeom.pmf(k, n_deck, n_success, n_draw)
    except Exception:
        return 0.0


def _hypergeom_cdf(n_deck, n_success, n_draw, k):
    if n_deck <= 0 or n_success <= 0 or n_draw <= 0:
        return 0.0
    if n_success > n_deck:
        n_success = n_deck
    try:
        return hypergeom.cdf(k, n_deck, n_success, n_draw)
    except Exception:
        return 0.0


def analyze_mana_ramp(deck_cards, deck_size=None, simulations=5000, assignments=None,
                       categories=None, triggers=None, card_triggers=None,
                       category_analysis_result=None):
    if deck_size is None:
        deck_size = len(deck_cards)

    lands = [c for c in deck_cards if _is_land(c)]
    land_count = len(lands)
    nonlands = [c for c in deck_cards if not _is_land(c)]
    avg_cmc = sum(c.get('cmc', 0) for c in nonlands) / len(nonlands) if nonlands else 0

    if category_analysis_result:
        return _analyze_mana_from_cat_result(
            deck_size, land_count, avg_cmc, categories or [],
            category_analysis_result,
        )

    if assignments and categories:
        return _analyze_mana_via_categories(
            deck_cards, deck_size, land_count, avg_cmc, simulations,
            assignments, categories, triggers, card_triggers,
        )

    return {
        'land_count': land_count,
        'avg_cmc': round(avg_cmc, 2),
        'total_ramp': 0,
        'total_draw': 0,
        'total_alcance': 0,
        'ramp_breakdown': {},
        'draw_breakdown': {},
        'alcance_breakdown': {},
        'by_turn': {},
    }


def _analyze_mana_via_categories(deck_cards, deck_size, land_count, avg_cmc, simulations,
                                  assignments, categories, triggers, card_triggers):
    from app.services.category_analysis import analyze_categories

    cat_result = analyze_categories(
        deck_size=deck_size,
        categories=categories,
        assignments=assignments,
        triggers=triggers or [],
        card_triggers=card_triggers,
    )

    ramp_cats = {c['id']: c for c in categories if c.get('config', {}).get('type') == 'ramp'}
    draw_cats = {c['id']: c for c in categories if c.get('config', {}).get('type') == 'draw'}
    alcance_cats = {c['id']: c for c in categories if c.get('config', {}).get('type') == 'alcance'}

    total_ramp = sum(s['cards_assigned'] for s in cat_result['categories'] if s['id'] in ramp_cats)
    total_draw = sum(s['cards_assigned'] for s in cat_result['categories'] if s['id'] in draw_cats)
    total_alcance = sum(s['cards_assigned'] for s in cat_result['categories'] if s['id'] in alcance_cats)

    ramp_breakdown = {}
    for s in cat_result['categories']:
        if s['id'] in ramp_cats:
            ramp_breakdown[s['name']] = s['cards_assigned']

    draw_breakdown = {}
    for s in cat_result['categories']:
        if s['id'] in draw_cats:
            draw_breakdown[s['name']] = s['cards_assigned']

    alcance_breakdown = {}
    for s in cat_result['categories']:
        if s['id'] in alcance_cats:
            alcance_breakdown[s['name']] = s['cards_assigned']

    results = {}
    for turn in range(1, 11):
        cards_drawn_by_turn = min(7 + (turn - 1), deck_size)

        prob_lands = []
        for k in range(0, min(land_count, cards_drawn_by_turn) + 1):
            prob_lands.append(_hypergeom_prob(deck_size, land_count, cards_drawn_by_turn, k))

        expected_lands = sum(k * p for k, p in enumerate(prob_lands))
        lands_in_play = min(expected_lands, turn)

        turn_data = cat_result['by_turn'].get(turn, {})
        cat_entries = turn_data.get('categories', {})

        ramp_contributions = {}
        total_ramp_mana = 0.0
        for cid, cat in ramp_cats.items():
            entry = cat_entries.get(cid, cat_entries.get(str(cid), {}))
            expected = float(entry.get('total_expected', 0))
            ramp_contributions[cat['name']] = round(expected, 2)
            total_ramp_mana += expected

        mana_from_lands = round(lands_in_play, 2)
        total_mana = round(mana_from_lands + total_ramp_mana, 2)

        p_land_drop = 1.0
        if land_count > 0:
            p_land_drop = 1 - _hypergeom_cdf(deck_size, land_count, cards_drawn_by_turn, turn - 1)

        cat_breakdown = {}
        for cid, entry in cat_entries.items():
            cid_int = int(cid) if not isinstance(cid, int) else cid
            info = next((c for c in categories if c['id'] == cid_int), None)
            if info:
                cat_breakdown[str(cid_int)] = {
                    'name': info['name'],
                    'color': info.get('color', '#6366f1'),
                    'type': info.get('config', {}).get('type', ''),
                    'expected': float(entry.get('expected', 0)),
                    'total_expected': float(entry.get('total_expected', 0)),
                    'prob_at_least_1': float(entry.get('prob_at_least_1', 0)),
                }

        results[turn] = {
            'turn': turn,
            'cards_drawn': cards_drawn_by_turn,
            'expected_lands_in_play': lands_in_play,
            'mana_from_lands': mana_from_lands,
            'ramp_contributions': ramp_contributions,
            'total_ramp_mana': round(total_ramp_mana, 2),
            'total_expected_mana': total_mana,
            'prob_hitting_land_drop': round(p_land_drop, 3),
            'categories': cat_breakdown,
        }

    return {
        'land_count': land_count,
        'avg_cmc': round(avg_cmc, 2),
        'total_ramp': total_ramp,
        'total_draw': total_draw,
        'total_alcance': total_alcance,
        'ramp_breakdown': ramp_breakdown,
        'draw_breakdown': draw_breakdown,
        'alcance_breakdown': alcance_breakdown,
        'category_summary': cat_result['categories'],
        'by_turn': results,
    }


def _analyze_mana_from_cat_result(deck_size, land_count, avg_cmc, categories, cat_result):
    ramp_cats = {c['id']: c for c in categories if c.get('config', {}).get('type') == 'ramp'}
    draw_cats = {c['id']: c for c in categories if c.get('config', {}).get('type') == 'draw'}
    alcance_cats = {c['id']: c for c in categories if c.get('config', {}).get('type') == 'alcance'}

    total_ramp = sum(s['cards_assigned'] for s in cat_result['categories'] if s['id'] in ramp_cats)
    total_draw = sum(s['cards_assigned'] for s in cat_result['categories'] if s['id'] in draw_cats)
    total_alcance = sum(s['cards_assigned'] for s in cat_result['categories'] if s['id'] in alcance_cats)

    ramp_breakdown = {}
    for s in cat_result['categories']:
        if s['id'] in ramp_cats:
            ramp_breakdown[s['name']] = s['cards_assigned']

    draw_breakdown = {}
    for s in cat_result['categories']:
        if s['id'] in draw_cats:
            draw_breakdown[s['name']] = s['cards_assigned']

    alcance_breakdown = {}
    for s in cat_result['categories']:
        if s['id'] in alcance_cats:
            alcance_breakdown[s['name']] = s['cards_assigned']

    results = {}
    for turn in range(1, 11):
        cards_drawn_by_turn = min(7 + (turn - 1), deck_size)

        prob_lands = []
        for k in range(0, min(land_count, cards_drawn_by_turn) + 1):
            prob_lands.append(_hypergeom_prob(deck_size, land_count, cards_drawn_by_turn, k))

        expected_lands = sum(k * p for k, p in enumerate(prob_lands))
        lands_in_play = min(expected_lands, turn)

        turn_data = cat_result['by_turn'].get(turn, {})
        cat_entries = turn_data.get('categories', {})

        ramp_contributions = {}
        total_ramp_mana = 0.0
        for cid, cat in ramp_cats.items():
            entry = cat_entries.get(cid, cat_entries.get(str(cid), {}))
            expected = float(entry.get('total_expected', 0))
            ramp_contributions[cat['name']] = round(expected, 2)
            total_ramp_mana += expected

        mana_from_lands = round(lands_in_play, 2)
        total_mana = round(mana_from_lands + total_ramp_mana, 2)

        p_land_drop = 1.0
        if land_count > 0:
            p_land_drop = 1 - _hypergeom_cdf(deck_size, land_count, cards_drawn_by_turn, turn - 1)

        cat_breakdown = {}
        for cid, entry in cat_entries.items():
            cid_int = int(cid) if not isinstance(cid, int) else cid
            info = next((c for c in categories if c['id'] == cid_int), None)
            if info:
                cat_breakdown[str(cid_int)] = {
                    'name': info['name'],
                    'color': info.get('color', '#6366f1'),
                    'type': info.get('config', {}).get('type', ''),
                    'expected': float(entry.get('expected', 0)),
                    'total_expected': float(entry.get('total_expected', 0)),
                    'prob_at_least_1': float(entry.get('prob_at_least_1', 0)),
                }

        results[turn] = {
            'turn': turn,
            'cards_drawn': cards_drawn_by_turn,
            'expected_lands_in_play': lands_in_play,
            'mana_from_lands': mana_from_lands,
            'ramp_contributions': ramp_contributions,
            'total_ramp_mana': round(total_ramp_mana, 2),
            'total_expected_mana': total_mana,
            'prob_hitting_land_drop': round(p_land_drop, 3),
            'categories': cat_breakdown,
        }

    return {
        'land_count': land_count,
        'avg_cmc': round(avg_cmc, 2),
        'total_ramp': total_ramp,
        'total_draw': total_draw,
        'total_alcance': total_alcance,
        'ramp_breakdown': ramp_breakdown,
        'draw_breakdown': draw_breakdown,
        'alcance_breakdown': alcance_breakdown,
        'category_summary': cat_result['categories'],
        'by_turn': results,
    }
