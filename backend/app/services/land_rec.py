"""
Land Recommendation Engine

Recommends optimal land count using a scaled version of Frank Karsten's
statistical formula. Ramp/draw counts come exclusively from category
assignments. No regex heuristics are used.

Core formula (for 60-card decks):
  Lands = 31.42 - 1.04 * Ramp_Spells + 0.52 * Avg_CMC + 0.84 * Draw_Spells

Scaling for non-60 formats:
  Commander (99 cards): multiply by 99/60
  Other sizes: multiply by deck_size/60

Color source recommendations based on pip count per color.
"""

from collections import defaultdict


def _is_land(card):
    tl = card.get('type_line', '')
    if not tl:
        return False
    tl_lower = tl.lower()
    if 'land' not in tl_lower:
        return False
    if '—' in tl:
        main_type = tl_lower.split('—')[0].strip()
        return 'land' in main_type
    return 'land' in tl_lower


def _avg_cmc(cards):
    nonlands = [c for c in cards if not _is_land(c)]
    if not nonlands:
        return 0
    return sum(c.get('cmc', 0) for c in nonlands) / len(nonlands)


def _count_from_assignments(assignments, cat_type):
    if not assignments:
        return 0
    from app.models.category import Category
    count = 0
    seen_card_ids = set()
    cat_type_cache = {}
    for a in assignments:
        cid = a.get('card_id')
        cat_id = a.get('category_id')
        if cat_id not in cat_type_cache:
            cat = Category.query.get(cat_id)
            cat_type_cache[cat_id] = cat.config.get('type', '') if cat and cat.config else ''
        if cat_type_cache[cat_id] == cat_type:
            if cid not in seen_card_ids:
                seen_card_ids.add(cid)
                count += 1
    return count


def recommend_lands(deck_cards, deck_size=None, assignments=None):
    if deck_size is None:
        deck_size = sum(c.get('quantity', 1) for c in deck_cards)

    expanded = []
    for c in deck_cards:
        qty = c.get('quantity', 1)
        expanded.extend([c] * qty)

    ramp_count = _count_from_assignments(assignments, 'ramp')
    draw_count = _count_from_assignments(assignments, 'draw')
    avg_cmc_val = _avg_cmc(expanded)

    if deck_size >= 99:
        base_lands = 34 + (avg_cmc_val * 0.4) - (ramp_count * 0.6) + min(draw_count, 6) * 0.2
        recommended = base_lands * (99 / 100)
    elif deck_size >= 80:
        base_lands = 30 + (avg_cmc_val * 0.4) - (ramp_count * 0.6) + min(draw_count, 6) * 0.2
        recommended = base_lands * (deck_size / 100)
    else:
        base_lands = 26 + (avg_cmc_val * 0.3) - (ramp_count * 0.4) + min(draw_count, 6) * 0.2
        recommended = base_lands

    recommended = max(deck_size * 0.25, min(deck_size * 0.45, recommended))
    recommended = round(recommended)

    low_risk = recommended - 1
    high_risk = recommended + 2

    colors_in_deck = set()
    for c in expanded:
        for color in c.get('color_identity', []):
            colors_in_deck.add(color)

    color_sources = {}
    if colors_in_deck:
        for color in sorted(colors_in_deck):
            needed = _recommend_color_sources(expanded, color, deck_size)
            color_sources[color] = needed

    mana_curve = defaultdict(int)
    for c in expanded:
        if _is_land(c):
            continue
        cmc = int(c.get('cmc', 0))
        if cmc > 12:
            cmc = 12
        mana_curve[cmc] += 1

    return {
        'recommended_lands': recommended,
        'range': {
            'low': low_risk,
            'high': high_risk,
        },
        'current_lands': sum(1 for c in expanded if _is_land(c)),
        'deck_size': deck_size,
        'avg_cmc': round(avg_cmc_val, 2),
        'ramp_count': ramp_count,
        'draw_count': draw_count,
        'profile': 'midrange',
        'adjustment_applied': 0,
        'formula': 'Frank Karsten (scaled)',
        'color_sources': color_sources,
        'mana_curve': dict(sorted(mana_curve.items())),
    }


def _recommend_color_sources(cards, color, deck_size):
    pips_needed = 0
    for c in cards:
        mc = c.get('mana_cost', '')
        pip_count = mc.count(f'{{{color.lower()}}}')
        if color == 'C':
            pip_count += mc.count('{C}')
        pips_needed += pip_count * c.get('quantity', 1)

    pips_needed = max(pips_needed, 1)

    if pips_needed <= 5:
        return 8
    elif pips_needed <= 10:
        return 12
    elif pips_needed <= 15:
        return 14
    elif pips_needed <= 23:
        return 16
    else:
        return 18
