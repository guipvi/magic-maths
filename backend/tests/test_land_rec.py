from app.services.land_rec import recommend_lands


def test_recommend_lands_returns_zero_ramp_count():
    cards = [
        {'name': 'Forest', 'type_line': 'Basic Land — Forest', 'oracle_text': '', 'cmc': 0, 'color_identity': ['G'], 'mana_cost': ''},
        {'name': 'Elvish Mystic', 'type_line': 'Creature — Elf Druid', 'oracle_text': '{T}: Add {G}', 'cmc': 1, 'color_identity': ['G'], 'mana_cost': '{G}'},
    ]
    result = recommend_lands(cards, deck_size=len(cards))
    assert result['ramp_count'] == 0
    assert result['draw_count'] == 0
    assert result['current_lands'] == 1
