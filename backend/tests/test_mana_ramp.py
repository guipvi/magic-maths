from app.services.mana_ramp import analyze_mana_ramp


def test_empty_by_turn_when_no_categories():
    cards = [
        {'name': 'Forest', 'type_line': 'Basic Land — Forest', 'oracle_text': '', 'cmc': 0},
        {'name': 'Elvish Mystic', 'type_line': 'Creature — Elf Druid', 'oracle_text': '{T}: Add {G}', 'cmc': 1},
    ]
    result = analyze_mana_ramp(cards, deck_size=len(cards))
    assert result['by_turn'] == {}
    assert result['land_count'] == 1
    assert result['total_ramp'] == 0
