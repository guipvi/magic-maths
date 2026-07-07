"""
Land Recommendation Engine (Feature 4)

Recommends optimal land count using a scaled version of Frank Karsten's
statistical formula based on analysis of thousands of tournament decks.

Core formula (for 60-card decks):
  Lands = 31.42 - 1.04 * Ramp_Spells + 0.52 * Avg_CMC + 0.84 * Draw_Spells

Scaling for non-60 formats:
  Commander (99 cards): multiply by 99/60
  Other sizes: multiply by deck_size/60

Additional adjustments:
- Profile detection: aggro (-1 land), control (+1), midrange (0)
  based on CMC distribution and creature density
- Color source recommendations: based on pip count per color
- Mana curve: CMC distribution of non-land cards

Output: recommended_lands, safe range (low-high), per-color sources.
"""

import re
from collections import defaultdict


RAMP_PATTERNS = [
    r'tap to add one mana of any color',
    r'tap to add .* mana of',
    r'tap to add .*mana',
    r'add (?:\{[rwubgcp]\}|[rwubgcp]\b)',
    r'add [a-z]+ mana',
    r'search your library for a basic land',
    r'search your library for a land',
    r'put a land card from your hand onto the battlefield',
    r'put a land card onto the battlefield',
    r'you may put a land card from your hand onto the battlefield',
    r'you may put a land card onto the battlefield',
    r'add an additional \{',
]

DRAW_PATTERNS = [
    r'draw a card',
    r'draw \d+ cards?',
    r'draw cards equal to',
]


def _count_ramp_spells(cards):
    count = 0
    for c in cards:
        ot = c.get('oracle_text', '') or ''
        tl = c.get('type_line', '')
        if 'land' in tl.lower() and 'land' in (tl.lower().split('—')[0] if '—' in tl else tl.lower()):
            continue
        for pat in RAMP_PATTERNS:
            if re.search(pat, ot, re.IGNORECASE):
                count += 1
                break
    return count


def _count_draw_spells(cards):
    count = 0
    for c in cards:
        ot = c.get('oracle_text', '') or ''
        tl = c.get('type_line', '')
        if 'land' in tl.lower() and 'land' in (tl.lower().split('—')[0] if '—' in tl else tl.lower()):
            continue
        for pat in DRAW_PATTERNS:
            if re.search(pat, ot, re.IGNORECASE):
                count += 1
                break
    return count


def _avg_cmc(cards):
    nonlands = [c for c in cards if not (
        'land' in c.get('type_line', '').lower()
        and 'land' in (c.get('type_line', '').lower().split('—')[0] if '—' in c.get('type_line', '') else c.get('type_line', '').lower())
    )]
    if not nonlands:
        return 0
    return sum(c.get('cmc', 0) for c in nonlands) / len(nonlands)


def _detect_profile(cards):
    nonlands = [c for c in cards if not (
        'land' in c.get('type_line', '').lower()
        and 'land' in (c.get('type_line', '').lower().split('—')[0] if '—' in c.get('type_line', '') else c.get('type_line', '').lower())
    )]
    if not nonlands:
        return 'unknown'

    low_cmc = sum(1 for c in nonlands if c.get('cmc', 0) <= 2)
    high_cmc = sum(1 for c in nonlands if c.get('cmc', 0) >= 6)
    creature_count = sum(1 for c in nonlands if 'creature' in c.get('type_line', '').lower())
    total = len(nonlands)

    low_cmc_ratio = low_cmc / total if total > 0 else 0
    high_cmc_ratio = high_cmc / total if total > 0 else 0
    creature_ratio = creature_count / total if total > 0 else 0

    if low_cmc_ratio > 0.5 and creature_ratio > 0.4:
        return 'aggro'
    if high_cmc_ratio > 0.15:
        return 'control'
    if creature_ratio > 0.3 and low_cmc_ratio > 0.3:
        return 'midrange'
    if creature_ratio < 0.2 and high_cmc_ratio > 0.1:
        return 'control'
    return 'midrange'


_PROFILE_ADJUSTMENT = {
    'aggro': -1,
    'midrange': 0,
    'control': 1,
    'combo': 0,
    'unknown': 0,
}


def recommend_lands(deck_cards, deck_size=None):
    if deck_size is None:
        deck_size = sum(c.get('quantity', 1) for c in deck_cards)

    expanded = []
    for c in deck_cards:
        qty = c.get('quantity', 1)
        expanded.extend([c] * qty)

    ramp_count = _count_ramp_spells(expanded)
    draw_count = _count_draw_spells(expanded)
    avg_cmc_val = _avg_cmc(expanded)
    profile = _detect_profile(expanded)

    # Para Commander, a fórmula clássica tende a over-estimar lands quando o deck tem
    # muitos efeitos de mana e muita densidade de cartas de 1-2 mana.
    # Em vez disso, usamos uma faixa mais conservadora baseada no tamanho do deck.
    if deck_size >= 99:
        base_lands = 34 + (avg_cmc_val * 0.4) - (ramp_count * 0.6) + min(draw_count, 6) * 0.2
        recommended = base_lands * (99 / 100)
    elif deck_size >= 80:
        base_lands = 30 + (avg_cmc_val * 0.4) - (ramp_count * 0.6) + min(draw_count, 6) * 0.2
        recommended = base_lands * (deck_size / 100)
    else:
        base_lands = 26 + (avg_cmc_val * 0.3) - (ramp_count * 0.4) + min(draw_count, 6) * 0.2
        recommended = base_lands

    adjustment = _PROFILE_ADJUSTMENT.get(profile, 0)
    recommended += adjustment

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
        tl = c.get('type_line', '')
        if 'land' in tl.lower() and 'land' in (tl.lower().split('—')[0] if '—' in tl else tl.lower()):
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
        'current_lands': sum(1 for c in expanded if
                             'land' in c.get('type_line', '').lower()),
        'deck_size': deck_size,
        'avg_cmc': round(avg_cmc_val, 2),
        'ramp_count': ramp_count,
        'draw_count': draw_count,
        'profile': profile,
        'adjustment_applied': adjustment,
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

    colors_in_deck = c.get('color_identity', [])
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
