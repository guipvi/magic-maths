from app.services.mana_ramp import analyze_mana_ramp


def test_basic_land_ramp_when_no_categories():
    cards = [
        {'name': 'Forest', 'type_line': 'Basic Land — Forest', 'oracle_text': '', 'cmc': 0},
        {'name': 'Elvish Mystic', 'type_line': 'Creature — Elf Druid', 'oracle_text': '{T}: Add {G}', 'cmc': 1},
    ]
    result = analyze_mana_ramp(cards, deck_size=len(cards))
    assert result['land_count'] == 1
    assert result['total_ramp'] == 0
    assert 1 in result['by_turn']
    assert result['by_turn'][1]['total_expected_mana'] == 1.0
    assert result['by_turn'][1]['expected_lands_in_play'] == 1.0
    assert result['by_turn'][1]['ramp_contributions'] == {}
