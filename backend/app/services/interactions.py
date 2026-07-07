"""
Interaction Analyzer (Feature 3)

Scans each non-land card's oracle_text using regex patterns to detect
and count interaction spells by type and target.

Interaction categories detected:
- destroy: destroy target [creature|artifact|enchantment|planeswalker|land]
- exile: exile target [same subtype]
- bounce: return to hand
- counter: counter target spell
- damage: deals damage to creature/any target
- graveyard: graveyard hate/exile
- tuck: put on bottom of library

Each interaction is cross-referenced with its target type (creature,
artifact, etc.) using keyword matching in the remaining oracle text.
Duplicates (same action + same target per card) are de-duplicated.
"""

import re

INTERACTION_PATTERNS = [
    ('destroy', [
        r'destroy target creature',
        r'destroy target artifact',
        r'destroy target enchantment',
        r'destroy target land',
        r'destroy target planeswalker',
        r'destroy target permanent',
        r'destroy all creatures',
        r'destroy all artifacts',
        r'destroy all enchantments',
    ]),
    ('exile', [
        r'exile target creature',
        r'exile target artifact',
        r'exile target enchantment',
        r'exile target land',
        r'exile target planeswalker',
        r'exile target permanent',
        r'exile all creatures',
        r'exile all artifacts',
        r'exile all enchantments',
        r'exile target.*battle',
    ]),
    ('bounce', [
        r'return target creature to (its owner\'s|owner\'s) hand',
        r'return target permanent to (its owner\'s|owner\'s) hand',
        r'return target nonland permanent',
        r'return all creatures to',
        r'return each creature to',
    ]),
    ('counter', [
        r'counter target spell',
        r'counter target creature spell',
        r'counter target noncreature spell',
        r'counter target instant spell',
        r'counter target sorcery spell',
        r'counter target activated ability',
        r'counter target triggered ability',
    ]),
    ('damage', [
        r'deals \d+ damage to target creature',
        r'deals \d+ damage to any target',
        r'deals \d+ damage to target.*creature',
        r'deals X damage to target',
    ]),
    ('graveyard', [
        r'exile target card from a graveyard',
        r'exile all cards from.*graveyard',
        r'exile target player\'s graveyard',
        r'exile target graveyard',
        r'target player exiles.*graveyard',
    ]),
    ('tuck', [
        r'put target.*on (the )?bottom of (its owner\'s|owner\'s) library',
        r'target.*library.*bottom',
    ]),
]

TYPE_MAPPING = {
    'creature': 'creature',
    'artifact': 'artifact',
    'enchantment': 'enchantment',
    'planeswalker': 'planeswalker',
    'land': 'land',
    'battle': 'battle',
    'instant': 'instant',
    'sorcery': 'sorcery',
}


def _extract_target_type(text, pattern):
    text_lower = text.lower()
    for perm_type, keywords in [
        ('creature', ['creature']),
        ('artifact', ['artifact']),
        ('enchantment', ['enchantment']),
        ('planeswalker', ['planeswalker']),
        ('land', ['land']),
        ('battle', ['battle']),
        ('permanent', ['permanent']),
        ('nonland permanent', ['nonland permanent', 'nonland']),
        ('spell', ['spell']),
        ('graveyard', ['graveyard']),
        ('any target', ['any target', 'any']),
    ]:
        for kw in keywords:
            if kw in text_lower:
                return perm_type
    return 'generic'


def analyze_interactions(deck_cards):
    classified = []
    for c in deck_cards:
        tl = c.get('type_line', '')
        ot = c.get('oracle_text', '') or ''
        name = c.get('name', '')

        if 'land' in tl.lower() and 'land' in (tl.lower().split('—')[0] if '—' in tl else tl.lower()):
            continue

        interactions = []

        for action, patterns in INTERACTION_PATTERNS:
            for pattern in patterns:
                if re.search(pattern, ot, re.IGNORECASE):
                    target_type = _extract_target_type(pattern, ot)
                    interactions.append({
                        'action': action,
                        'target_type': target_type,
                        'pattern_matched': pattern,
                    })

        if interactions:
            classified.append({
                'name': name,
                'type_line': tl,
                'cmc': c.get('cmc', 0),
                'oracle_text': ot,
                'interactions': interactions,
            })

    summary = {}
    for action in ['destroy', 'exile', 'bounce', 'counter', 'damage', 'graveyard', 'tuck']:
        summary[action] = {
            'total': 0,
            'by_target': {},
        }
        for target in ['creature', 'artifact', 'enchantment', 'planeswalker',
                       'land', 'battle', 'permanent', 'nonland permanent',
                       'spell', 'graveyard', 'any target', 'generic']:
            summary[action]['by_target'][target] = 0

    for entry in classified:
        seen = set()
        for interaction in entry['interactions']:
            key = (interaction['action'], interaction['target_type'])
            if key not in seen:
                seen.add(key)
                summary[interaction['action']]['total'] += 1
                target = interaction['target_type']
                if target in summary[interaction['action']]['by_target']:
                    summary[interaction['action']]['by_target'][target] += 1

    total_interaction_spells = len(classified)

    return {
        'total_interaction_spells': total_interaction_spells,
        'breakdown': summary,
        'spells': classified,
        'total_removal': summary['destroy']['total'] + summary['exile']['total'] + summary['bounce']['total'],
        'total_counterspells': summary['counter']['total'],
        'total_graveyard_hate': summary['graveyard']['total'],
    }
