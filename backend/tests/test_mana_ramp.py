from app.services.mana_ramp import classify_card


def test_classify_card_detects_sol_ring_as_mana_rock():
    card = {
        'name': 'Sol Ring',
        'type_line': 'Artifact',
        'oracle_text': '{T}: Add C',
        'cmc': 1,
    }

    result = classify_card(card)

    assert 'rock_fixed' in result['classifications']['ramp']
