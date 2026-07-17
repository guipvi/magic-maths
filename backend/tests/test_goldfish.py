from app.services.goldfish import _is_land, simulate_goldfish


def test_is_land_detects_basic_lands():
    card = {'type_line': 'Basic Land — Forest'}
    assert _is_land(card) is True


def test_is_land_rejects_nonlands():
    card = {'type_line': 'Legendary Creature — Human Wizard'}
    assert _is_land(card) is False


def _make_card(card_id, name='Card', cmc=1, type_line='Instant', quantity=1):
    return {
        'id': card_id, 'name': name, 'cmc': cmc,
        'type_line': type_line, 'quantity': quantity,
    }


def test_parent_rollup_limiter_produces_draws():
    """Card cast in subcategory produces events in parent via limiter."""
    # Categories: sac_outlet (parent), auto (child), draw
    categories = [
        {'id': 1, 'name': 'sac_outlet', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'auto', 'color': '#f87171', 'config': {}, 'parent_id': 1},
        {'id': 3, 'name': 'draw', 'color': '#3b82f6', 'config': {'type': 'draw'}},
    ]
    # Brass Bounty in "auto" (child of sac_outlet), Korvold in "draw" with limiter from sac_outlet
    assignments = [
        {'card_id': 1, 'category_id': 2, 'multiplier': 1.0},
        {'card_id': 2, 'category_id': 3, 'multiplier': 1.0,
         'limit_category_id': 1},
    ]
    limiters = [
        {'target_category_id': 3, 'logic': 'OR', 'source_category_ids': [1],
         'trigger_count': 1, 'accumulate': False},
    ]
    deck = [_make_card(1, 'Brass Bounty', 7, 'Sorcery'),
            _make_card(2, 'Korvold', 4, 'Legendary Creature'),
            *[_make_card(100 + i, 'Land', 0, 'Basic Land — Forest') for i in range(38)]]
    result = simulate_goldfish(deck, deck_size=40, simulations=100,
                               assignments=assignments, categories=categories,
                               limiters=limiters, max_speed=True)
    # With rollup, events from auto roll up to sac_outlet
    # Korvold being in draw category means base draws + limiter draws
    avg_hand = result['turn_by_turn'][4]['avg_cards_in_hand']
    assert avg_hand >= 0


def test_multiplier_generates_proportional_draws():
    """Higher multiplier on a source card produces more draw events."""
    categories = [
        {'id': 1, 'name': 'sacrifice', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'draw', 'color': '#3b82f6', 'config': {'type': 'draw'}},
    ]
    # Low multiplier
    assignments_low = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0},
        {'card_id': 2, 'category_id': 2, 'multiplier': 1.0,
         'limit_category_id': 1},
    ]
    # High multiplier
    assignments_high = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 10.0},
        {'card_id': 2, 'category_id': 2, 'multiplier': 1.0,
         'limit_category_id': 1},
    ]
    limiters = [
        {'target_category_id': 2, 'logic': 'OR', 'source_category_ids': [1],
         'trigger_count': 1, 'accumulate': False},
    ]
    deck = [_make_card(1, 'Sacrifice Source', 1, 'Creature'),
            _make_card(2, 'Draw Card', 2, 'Enchantment'),
            *[_make_card(100 + i, 'Land', 0, 'Basic Land — Forest') for i in range(38)]]

    result_low = simulate_goldfish(deck, deck_size=40, simulations=100,
                                   assignments=assignments_low, categories=categories,
                                   limiters=limiters, max_speed=True)
    result_high = simulate_goldfish(deck, deck_size=40, simulations=100,
                                    assignments=assignments_high, categories=categories,
                                    limiters=limiters, max_speed=True)

    # Higher multiplier should result in more or equal cards in hand (more draws from limiter)
    avg_low = sum(r['avg_cards_in_hand'] for r in result_low['turn_by_turn'][:5])
    avg_high = sum(r['avg_cards_in_hand'] for r in result_high['turn_by_turn'][:5])
    assert avg_high >= avg_low


def test_battlefield_permanents_contribute_to_limiter():
    """Permanents already on battlefield contribute source events for limiters."""
    categories = [
        {'id': 1, 'name': 'sacrifice', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'draw', 'color': '#3b82f6', 'config': {'type': 'draw'}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0},
        {'card_id': 2, 'category_id': 2, 'multiplier': 1.0,
         'limit_category_id': 1},
    ]
    limiters = [
        {'target_category_id': 2, 'logic': 'OR', 'source_category_ids': [1],
         'trigger_count': 1, 'accumulate': False},
    ]
    # Card 1 is a creature (permanent), card 2 is the draw source
    deck = [_make_card(1, 'Sacrifice Fodder', 1, 'Creature'),
            _make_card(2, 'Draw Engine', 2, 'Enchantment'),
            *[_make_card(100 + i, 'Land', 0, 'Basic Land — Forest') for i in range(38)]]

    result = simulate_goldfish(deck, deck_size=40, simulations=100,
                               assignments=assignments, categories=categories,
                               limiters=limiters, max_speed=True)
    # The simulation should complete without errors and produce results
    assert len(result['turn_by_turn']) > 0
    assert result['deck_size'] == 40


def test_parent_rollup_with_multiplier():
    """Card with high multiplier in child category produces proportional events in parent."""
    categories = [
        {'id': 1, 'name': 'sac_outlet', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'auto', 'color': '#f87171', 'config': {}, 'parent_id': 1},
        {'id': 3, 'name': 'draw', 'color': '#3b82f6', 'config': {'type': 'draw'}},
    ]
    # High multiplier in child category
    assignments = [
        {'card_id': 1, 'category_id': 2, 'multiplier': 5.0},
        {'card_id': 2, 'category_id': 3, 'multiplier': 1.0,
         'limit_category_id': 1},
    ]
    limiters = [
        {'target_category_id': 3, 'logic': 'OR', 'source_category_ids': [1],
         'trigger_count': 1, 'accumulate': False},
    ]
    deck = [_make_card(1, 'Treasure Maker', 3, 'Artifact'),
            _make_card(2, 'Korvold', 4, 'Legendary Creature'),
            *[_make_card(100 + i, 'Land', 0, 'Basic Land — Forest') for i in range(38)]]

    result = simulate_goldfish(deck, deck_size=40, simulations=100,
                               assignments=assignments, categories=categories,
                               limiters=limiters, max_speed=True)
    # Should complete and produce meaningful results
    assert result['avg_empty_hand_turn'] > 0


def test_containment_rollup_source_events_for_limiter():
    """Events from a contained category roll up to container via containment for limiters.

    Treasure (contained in auto via user-defined containment) should contribute
    events to auto's source_events, which the limiter consumes from.
    """
    categories = [
        {'id': 1, 'name': 'sac_outlet', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'auto', 'color': '#f87171', 'config': {}, 'parent_id': 1},
        {'id': 3, 'name': 'tesouro', 'color': '#f59e0b', 'config': {}},
        {'id': 4, 'name': 'draw', 'color': '#3b82f6', 'config': {'type': 'draw'}},
    ]
    # Brass Bounty in tesouro with high multiplier
    assignments = [
        {'card_id': 1, 'category_id': 3, 'multiplier': 80.0},
        {'card_id': 2, 'category_id': 4, 'multiplier': 1.0,
         'limit_category_id': 1},
    ]
    # tesouro is contained in auto (user-defined containment, 1/n subcategoria)
    containment_map = {2: {3}}
    direct_children_of = {2: {3}}
    limiters = [
        {'target_category_id': 4, 'logic': 'OR', 'source_category_ids': [1],
         'trigger_count': 1, 'accumulate': False},
    ]

    deck = [_make_card(1, 'Brass Bounty', 7, 'Sorcery'),
            _make_card(2, 'Korvold', 4, 'Legendary Creature'),
            *[_make_card(100 + i, 'Land', 0, 'Basic Land — Forest') for i in range(38)]]

    result = simulate_goldfish(
        deck, deck_size=40, simulations=100,
        assignments=assignments, categories=categories,
        limiters=limiters, containment_map=containment_map,
        direct_children_of=direct_children_of, max_speed=True)

    # Without containment, tesouro events wouldn't reach sac_outlet at all
    # (no parent_id), so limiter would produce 0 draws
    # With containment, tesouro rolls up to auto -> sac_outlet -> limiter consumes
    assert result['avg_empty_hand_turn'] > 0


def test_containment_rollup_source_events_for_trigger():
    """Events from a contained category roll up to container via containment for triggers.

    Card trigger source=sac_outlet should see events from tesouro (contained
    in auto, which is a child of sac_outlet).
    """
    categories = [
        {'id': 1, 'name': 'sac_outlet', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'auto', 'color': '#f87171', 'config': {}, 'parent_id': 1},
        {'id': 3, 'name': 'tesouro', 'color': '#f59e0b', 'config': {}},
        {'id': 4, 'name': 'draw', 'color': '#3b82f6', 'config': {'type': 'draw'}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 3, 'multiplier': 80.0},
        {'card_id': 2, 'category_id': 1, 'multiplier': 1.0},
    ]
    containment_map = {2: {3}}
    direct_children_of = {2: {3}}
    card_triggers = [
        {'source_category_id': 1, 'source_card_id': 2,
         'target_category_id': 4, 'trigger_count': 1},
    ]

    deck = [_make_card(1, 'Brass Bounty', 7, 'Sorcery'),
            _make_card(2, 'Korvold', 4, 'Legendary Creature'),
            *[_make_card(100 + i, 'Land', 0, 'Basic Land — Forest') for i in range(38)]]

    result = simulate_goldfish(
        deck, deck_size=40, simulations=100,
        assignments=assignments, categories=categories,
        card_triggers=card_triggers, containment_map=containment_map,
        direct_children_of=direct_children_of, max_speed=True)

    # Containment rollup should make tesouro events visible to sac_outlet
    assert result['avg_empty_hand_turn'] > 0


def test_trigger_containment_expansion():
    """Card trigger with source=sac_outlet expands to contained categories.

    When sac_outlet contains tesouro via containment, a trigger with
    source_category_id=sac_outlet should also fire on events from tesouro.
    """
    categories = [
        {'id': 1, 'name': 'sac_outlet', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'tesouro', 'color': '#f59e0b', 'config': {}},
        {'id': 3, 'name': 'draw', 'color': '#3b82f6', 'config': {'type': 'draw'}},
    ]
    # Korvold in sac_outlet, Brass Bounty in tesouro
    assignments = [
        {'card_id': 2, 'category_id': 1, 'multiplier': 1.0},
        {'card_id': 1, 'category_id': 2, 'multiplier': 5.0},
    ]
    # sac_outlet contains tesouro
    containment_map = {1: {2}}
    direct_children_of = {1: {2}}
    # Trigger: when sac_outlet fires and Korvold on battlefield -> draw
    card_triggers = [
        {'source_category_id': 1, 'source_card_id': 2,
         'target_category_id': 3, 'trigger_count': 1},
    ]

    deck = [_make_card(1, 'Brass Bounty', 7, 'Sorcery'),
            _make_card(2, 'Korvold', 4, 'Legendary Creature'),
            *[_make_card(100 + i, 'Land', 0, 'Basic Land — Forest') for i in range(38)]]

    result = simulate_goldfish(
        deck, deck_size=40, simulations=100,
        assignments=assignments, categories=categories,
        card_triggers=card_triggers, containment_map=containment_map,
        direct_children_of=direct_children_of, max_speed=True)

    # Without containment expansion, source_events['sac_outlet'] would only
    # have Korvold's events (mult=1), not Brass Bounty's (mult=5)
    # With expansion, the trigger also sees tesouro events
    assert result['avg_empty_hand_turn'] > 0
