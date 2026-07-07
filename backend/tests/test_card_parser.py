from app.utils.card_parser import parse_decklist


def test_parse_decklist_supports_x_suffix_and_sideboard():
    decklist = """// Name: Test Deck
1x Sol Ring
4 Lightning Bolt
2x Island

Sideboard
2 Pyroblast
1x Tormod's Crypt
"""

    parsed = parse_decklist(decklist)

    assert parsed['name'] == 'Test Deck'
    assert parsed['mainboard'][0]['name'] == 'Sol Ring'
    assert parsed['mainboard'][0]['quantity'] == 1
    assert parsed['mainboard'][1]['name'] == 'Lightning Bolt'
    assert parsed['mainboard'][1]['quantity'] == 4
    assert parsed['mainboard'][2]['name'] == 'Island'
    assert parsed['mainboard'][2]['quantity'] == 2
    assert parsed['sideboard'][0]['name'] == 'Pyroblast'
    assert parsed['sideboard'][0]['quantity'] == 2
    assert parsed['sideboard'][1]['name'] == "Tormod's Crypt"
    assert parsed['sideboard'][1]['quantity'] == 1
