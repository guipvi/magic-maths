"""Interaction Analyzer

Interactions are now defined manually via category assignments.
This service reads category assignments and derives interaction
data from the categories marked as type 'interaction'.
"""

from app.models.category import Category, DeckCardCategory

INTERACTION_ACTIONS = [
    'destroy', 'exile', 'bounce', 'counter', 'damage', 'graveyard', 'tuck',
]


def analyze_interactions_from_assignments(deck_id, deck_cards):
    """Analyze interactions based on manual category assignments."""
    interaction_cats = Category.query.filter(
        Category.config['type'].as_string() == 'interaction'
    ).all()

    cat_map = {c.id: c for c in interaction_cats}
    cat_ids = list(cat_map.keys())

    if not cat_ids:
        return _empty_result()

    assignments = DeckCardCategory.query.filter(
        DeckCardCategory.deck_id == deck_id,
        DeckCardCategory.category_id.in_(cat_ids),
    ).all()

    card_counts = {}
    for c in deck_cards:
        cid = c.get('id')
        card_counts[cid] = card_counts.get(cid, 0) + 1

    spells = []
    seen_card_cat = set()

    card_assignments = {}
    for a in assignments:
        key = (a.card_id, a.category_id)
        if key not in seen_card_cat:
            seen_card_cat.add(key)
            qty = card_counts.get(a.card_id, 1)
            card_assignments[key] = qty
        else:
            card_assignments[key] = card_assignments.get(key, 0) + card_counts.get(a.card_id, 1)

    for (card_id, cat_id), qty in card_assignments.items():
        cat = cat_map.get(cat_id)
        if not cat:
            continue
        for c in deck_cards:
            if c.get('id') == card_id:
                for _ in range(qty):
                    spells.append({
                        'name': c.get('name', ''),
                        'type_line': c.get('type_line', ''),
                        'oracle_text': c.get('oracle_text', ''),
                        'cmc': c.get('cmc', 0),
                        'interactions': [{
                            'action': cat.name,
                            'target_type': 'manual',
                        }],
                    })
                break

    summary = {}
    for action in INTERACTION_ACTIONS:
        summary[action] = {'total': 0, 'by_target': {'manual': 0}}
        for cat in interaction_cats:
            if cat.name == action:
                total = sum(
                    aqty
                    for (_, cid2), aqty in card_assignments.items()
                    if cid2 == cat.id
                )
                summary[action]['total'] = total
                summary[action]['by_target']['manual'] = total

    total_interaction_spells = sum(
        s['total'] for s in summary.values()
    )

    return {
        'total_interaction_spells': total_interaction_spells,
        'breakdown': summary,
        'spells': spells,
        'total_removal': (summary['destroy']['total'] +
                          summary['exile']['total'] +
                          summary['bounce']['total']),
        'total_counterspells': summary['counter']['total'],
        'total_graveyard_hate': summary['graveyard']['total'],
    }


def _empty_result():
    summary = {}
    for action in INTERACTION_ACTIONS:
        summary[action] = {'total': 0, 'by_target': {'manual': 0}}
    return {
        'total_interaction_spells': 0,
        'breakdown': summary,
        'spells': [],
        'total_removal': 0,
        'total_counterspells': 0,
        'total_graveyard_hate': 0,
    }
