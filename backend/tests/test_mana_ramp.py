from app.services.mana_ramp import classify_card, analyze_mana_ramp


def test_classify_card_detects_sol_ring_as_mana_rock():
    card = {
        'name': 'Sol Ring',
        'type_line': 'Artifact',
        'oracle_text': '{T}: Add C',
        'cmc': 1,
    }

    result = classify_card(card)

    assert 'rock_fixed' in result['classifications']['ramp']


def test_turn_3_mana_is_not_overcounted_by_all_ramp_spells():
    cards = []
    for _ in range(3):
        cards.append({
            'name': 'Forest',
            'type_line': 'Basic Land — Forest',
            'oracle_text': '',
            'cmc': 0,
        })
    for _ in range(3):
        cards.append({
            'name': 'Elvish Mystic',
            'type_line': 'Creature — Elf Druid',
            'oracle_text': '{T}: Add {G}',
            'cmc': 1,
        })
    for _ in range(3):
        cards.append({
            'name': 'Rampant Growth',
            'type_line': 'Sorcery',
            'oracle_text': 'Search your library for a basic land card, put it onto the battlefield tapped, then shuffle.',
            'cmc': 2,
        })

    result = analyze_mana_ramp(cards, deck_size=len(cards))

    # 3 lands (3 mana) + 3 dorks (3 mana) = 6; land ramp só conta do turno 4+
    assert result['by_turn'][3]['total_expected_mana'] == 6


def test_deathsprout_one_word_is_classified_as_land_ramp():
    card = {
        'name': 'Deathsprout',
        'type_line': 'Instant',
        'oracle_text': 'Destroy target creature. Search your library for a basic land card, put it onto the battlefield tapped, then shuffle.',
        'cmc': 4,
    }

    result = classify_card(card)

    assert 'land_ramp_basic' in result['classifications']['ramp']


def test_tutored_lands_count_as_mana_from_turn_4_onward():
    cards = [
        {
            'name': 'Forest',
            'type_line': 'Basic Land — Forest',
            'oracle_text': '',
            'cmc': 0,
        },
        {
            'name': 'Rampant Growth',
            'type_line': 'Sorcery',
            'oracle_text': 'Search your library for a basic land card, put it onto the battlefield tapped, then shuffle.',
            'cmc': 2,
        },
    ]

    result = analyze_mana_ramp(cards, deck_size=len(cards))

    assert result['by_turn'][4]['mana_from_land_ramp'] == 1
    assert result['by_turn'][4]['total_expected_mana'] >= 2
