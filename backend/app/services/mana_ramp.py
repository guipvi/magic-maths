"""
Mana Ramp Prediction Engine (Feature 1)

Predicts available mana per turn using two complementary approaches:

1. Hypergeometric Distribution (analytical):
   - Calculates exact probability of drawing K lands by turn N
   - Estimates expected lands in play each turn
   - Separates mana sources: lands, dorks, rocks, land ramp, rituals
   - Computes probability of hitting each land drop

2. Monte Carlo Simulation (empirical):
   - Runs N=5000 simulated games
   - Each sim: shuffle deck, draw 7, play land+ramp each turn
   - Tracks mana distribution across simulations
   - Returns percentiles (P10, P50, P90) for each turn

Card classification regex patterns match against oracle_text to
categorize each spell into ramp/draw/manipulation subtypes.
"""

import numpy as np
from scipy.stats import hypergeom


RAMP_PATTERNS = [
    (r'tap to add one mana of any color', 'rock_fixed'),
    (r'tap to add .* mana of', 'rock_fixed'),
    (r'tap to add .*mana', 'rock_any'),
    (r'add (?:\{[rwubgcp]\}|[rwubgcp])\b', 'rock_fixed'),
    (r'add (?:\{[rwubgcp]\}|[rwubgcp])\b.*add (?:\{[rwubgcp]\}|[rwubgcp])\b', 'ritual'),
    (r'add (?:\{[rwubgcp]\}|[rwubgcp])\b.*(?:\{[rwubgcp]\}|[rwubgcp])\b', 'ritual'),
    (r'search your library for a basic land', 'land_ramp_basic'),
    (r'search your library for a land', 'land_ramp_any'),
    (r'you may put a land card from your hand onto the battlefield', 'extra_land'),
    (r'you may put a land card onto the battlefield', 'land_ramp_direct'),
    (r'add an additional \{', 'extra_mana'),
    (r'costs \{.\} less to cast', 'cost_reducer'),
]

DRAW_PATTERNS = [
    (r'draw a card', 'cantrip'),
    (r'draw \d+ cards?', 'draw_spell'),
    (r'draw cards equal to', 'draw_x'),
    (r'discard your hand.*draw', 'wheel'),
    (r'looting', 'looting'),
    (r' Surveil ', 'surveil'),
    (r' Scry \d+', 'scry'),
    (r'look at the top \d+', 'topdeck_look'),
    (r'put.*on (the )?top of (your )?library', 'topdeck_put'),
]


def _is_land(card):
    tl = card.get('type_line', '')
    return 'land' in tl.lower() and 'land' not in tl.lower().split('—')[0] if '—' in tl else 'land' in tl.lower()


def _is_land_or_ramp(card):
    return _is_land(card) or card.get('cmc', 999) == 0


def classify_card(card):
    tl = card.get('type_line', '')
    ot = card.get('oracle_text', '') or ''
    name = card.get('name', '')
    cmc = card.get('cmc', 0)
    tl_lower = tl.lower()

    if 'land' in tl_lower:
        return {'category': 'land', 'subtype': 'basic' if 'basic' in tl_lower else 'nonbasic'}
    if 'battle' in tl_lower and 'battle' in tl_lower.split('—')[0] if '—' in tl_lower else False:
        return {'category': 'battle', 'subtype': 'battle'}

    classifications = {'ramp': [], 'draw': [], 'manipulation': [], 'interaction': []}

    for pattern, label in RAMP_PATTERNS:
        import re
        if re.search(pattern, ot, re.IGNORECASE):
            classifications['ramp'].append(label)

    if not classifications['ramp']:
        if re.search(r'add (?:\{[rwubgcp]\}|[rwubgcp])\b', ot, re.IGNORECASE):
            classifications['ramp'].append('rock_fixed')
        elif re.search(r'add [a-z]+ mana', ot, re.IGNORECASE):
            classifications['ramp'].append('rock_fixed')

    for pattern, label in DRAW_PATTERNS:
        import re
        if re.search(pattern, ot, re.IGNORECASE):
            classifications['draw'].append(label)

    category = 'other'
    if 'creature' in tl_lower:
        category = 'creature'
    elif 'instant' in tl_lower:
        category = 'instant'
    elif 'sorcery' in tl_lower:
        category = 'sorcery'
    elif 'artifact' in tl_lower:
        category = 'artifact'
    elif 'enchantment' in tl_lower:
        category = 'enchantment'
    elif 'planeswalker' in tl_lower:
        category = 'planeswalker'

    return {
        'category': category,
        'cmc': cmc,
        'name': name,
        'type_line': tl,
        'oracle_text': ot,
        'classifications': classifications,
    }


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


_MANA_BY_TURN_MAP = {
    'dork': lambda turn, count: count if turn >= 2 else 0,
    'rock_any': lambda turn, count: count if turn >= 2 else 0,
    'rock_fixed': lambda turn, count: count if turn >= 2 else 0,
    'land_ramp_basic': lambda turn, count: count if turn >= 3 else 0,
    'land_ramp_any': lambda turn, count: count if turn >= 3 else 0,
    'land_ramp_direct': lambda turn, count: count if turn >= 3 else 0,
    'extra_land': lambda turn, count: count if turn >= 2 else 0,
    'extra_mana': lambda turn, count: count if turn >= 3 else 0,
    'cost_reducer': lambda turn, count: count if turn >= 2 else 0,
    'ritual': lambda turn, count: (count if turn >= 1 else 0) * 2,
}


def analyze_mana_ramp(deck_cards, deck_size=None, simulations=5000):
    classified = [classify_card(c) for c in deck_cards]

    if deck_size is None:
        deck_size = len(deck_cards)

    lands = [c for c in classified if c['category'] == 'land']
    land_count = sum(1 for _ in lands)
    nonlands = [c for c in classified if c['category'] != 'land']

    ramp_counts = {'dork': 0, 'rock_fixed': 0, 'rock_any': 0, 'land_ramp_basic': 0,
                   'land_ramp_any': 0, 'land_ramp_direct': 0, 'extra_land': 0,
                   'extra_mana': 0, 'cost_reducer': 0, 'ritual': 0}
    draw_counts = {'cantrip': 0, 'draw_spell': 0, 'draw_x': 0, 'wheel': 0, 'looting': 0}
    manipulation_counts = {'scry': 0, 'surveil': 0, 'topdeck_look': 0, 'topdeck_put': 0}

    avg_cmc = 0
    total_nonland = 0
    for c in nonlands:
        if c['cmc'] > 0:
            total_nonland += 1
            avg_cmc += c['cmc']
        for r_type in c['classifications']['ramp']:
            if r_type in ramp_counts:
                ramp_counts[r_type] += 1
        for d_type in c['classifications']['draw']:
            if d_type in draw_counts:
                draw_counts[d_type] += 1
            if d_type in manipulation_counts:
                manipulation_counts[d_type] += 1
        for m_type in c['classifications']['manipulation']:
            if m_type in manipulation_counts:
                manipulation_counts[m_type] += 1

    if total_nonland > 0:
        avg_cmc /= total_nonland

    total_ramp = sum(ramp_counts.values())
    mana_dorks = ramp_counts.get('dork', 0)
    mana_rocks = ramp_counts.get('rock_fixed', 0) + ramp_counts.get('rock_any', 0)
    land_ramps = (ramp_counts.get('land_ramp_basic', 0) +
                  ramp_counts.get('land_ramp_any', 0) +
                  ramp_counts.get('land_ramp_direct', 0))
    fast_mana = ramp_counts.get('ritual', 0)

    results = {}
    for turn in range(1, 11):
        cards_drawn_by_turn = 7 + (turn - 1)
        if cards_drawn_by_turn > deck_size:
            cards_drawn_by_turn = deck_size

        prob_lands = []
        for k in range(0, min(land_count, cards_drawn_by_turn) + 1):
            prob_lands.append(_hypergeom_prob(deck_size, land_count, cards_drawn_by_turn, k))

        expected_lands = sum(k * p for k, p in enumerate(prob_lands))
        # on the play, you play one land per turn (approximately)
        lands_in_play = min(expected_lands, turn)

        mana_from_lands = lands_in_play
        mana_from_dorks = mana_dorks if turn >= 2 else 0
        mana_from_rocks = mana_rocks if turn >= 2 else 0

        land_ramp_value = 0
        if turn >= 3:
            land_ramp_value = min(land_ramps, 1)

        total_mana = mana_from_lands + mana_from_dorks + mana_from_rocks + land_ramp_value
        if fast_mana > 0 and turn >= 1 and turn <= 3:
            total_mana += min(fast_mana, 1) * 2

        p_land_drop = 1.0
        if land_count > 0:
            p_land_drop = 1 - _hypergeom_cdf(deck_size, land_count, cards_drawn_by_turn, turn - 1)

        results[turn] = {
            'turn': turn,
            'cards_drawn': cards_drawn_by_turn,
            'expected_lands_in_hand': round(expected_lands, 2),
            'expected_lands_in_play': round(lands_in_play, 2),
            'mana_from_lands': round(mana_from_lands, 2),
            'mana_from_dorks': mana_from_dorks,
            'mana_from_rocks': mana_from_rocks,
            'mana_from_land_ramp': land_ramp_value,
            'mana_from_rituals': fast_mana * 2 if turn >= 1 else 0,
            'total_expected_mana': round(total_mana, 2),
            'prob_hitting_land_drop': round(p_land_drop, 3),
            'mana_percentiles': _simulate_mana(deck_cards, land_count, total_ramp,
                                                deck_size, turn, simulations),
        }

    return {
        'land_count': land_count,
        'avg_cmc': round(avg_cmc, 2),
        'total_ramp': total_ramp,
        'ramp_breakdown': ramp_counts,
        'draw_breakdown': draw_counts,
        'manipulation_breakdown': manipulation_counts,
        'by_turn': results,
    }


def _simulate_mana(deck_cards, land_count, ramp_count, deck_size, turn, n_sims=5000):
    nonland_count = deck_size - land_count

    if n_sims <= 0 or deck_size <= 0:
        return {'p10': 0, 'p50': 0, 'p90': 0}

    rng = np.random.default_rng(42)
    mana_each_turn = []

    for _ in range(n_sims):
        deck = ['L'] * land_count + ['R'] * ramp_count + ['O'] * (nonland_count - ramp_count)
        rng.shuffle(deck)

        hand = deck[:7]
        library = deck[7:]
        lands_played = 0
        mana = 0
        total_mana = 0

        for t in range(1, turn + 1):
            if t > 1 and library:
                drawn = library.pop(0)
                hand.append(drawn)

            land_in_hand = hand.count('L')
            ramp_in_hand = hand.count('R')

            if land_in_hand > 0:
                hand.remove('L')
                lands_played += 1
                mana = lands_played

            ramp_used = 0
            if t >= 2 and ramp_in_hand > 0 and lands_played >= 1:
                ramp_used = min(ramp_in_hand, 1)
                for _ in range(ramp_used):
                    if 'R' in hand:
                        hand.remove('R')
                mana += 1

            if t >= 3 and ramp_in_hand > 1 and lands_played >= 2:
                extra_ramp = ramp_in_hand - 1
                to_use = min(extra_ramp, 1)
                if to_use > 0 and 'R' in hand:
                    hand.remove('R')
                    mana += 1

            total_mana += mana

        mana_each_turn.append(mana)

    if not mana_each_turn:
        return {'p10': 0, 'p50': 0, 'p90': 0}

    arr = np.array(mana_each_turn)
    return {
        'p10': round(float(np.percentile(arr, 10)), 2),
        'p50': round(float(np.percentile(arr, 50)), 2),
        'p90': round(float(np.percentile(arr, 90)), 2),
    }
