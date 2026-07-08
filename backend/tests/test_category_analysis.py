import pytest
from app.services.category_analysis import analyze_categories


def test_empty_deck():
    result = analyze_categories(deck_size=0, categories=[], assignments=[], triggers=[])
    assert result['deck_size'] == 0
    # still produces 10 turns of empty data
    for t in range(1, 11):
        assert result['by_turn'][t]['categories'] == {}


def test_basic_category_counts():
    categories = [{'id': 1, 'name': 'ramp', 'color': '#22c55e', 'config': {'type': 'ramp'}}]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    result = analyze_categories(deck_size=40, categories=categories, assignments=assignments, triggers=[])

    assert result['categories'][0]['cards_assigned'] == 2
    assert result['categories'][0]['total_multiplier_sum'] == 2.0

    t1 = result['by_turn'][1]
    cat_data = t1['categories'][1]
    # With 40 cards, 2 ramps, drawing 7: expected = 7 * 2/40 = 0.35
    assert abs(cat_data['expected'] - 0.35) < 0.01
    assert cat_data['total_expected'] == cat_data['expected']  # no triggers


def test_multiplier_effect():
    categories = [{'id': 1, 'name': 'ramp', 'color': '#22c55e', 'config': {'type': 'ramp'}}]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 3.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments, triggers=[])

    assert result['categories'][0]['total_multiplier_sum'] == 3.0
    t1 = result['by_turn'][1]['categories'][1]
    # Expected: 7 * (3.0/60) = 0.35
    assert abs(t1['expected'] - 0.35) < 0.01


def test_triggers_increase_target():
    categories = [
        {'id': 1, 'name': 'criatura', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'draw', 'color': '#3b82f6', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 2, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    triggers = [
        {'source_category_id': 1, 'target_category_id': 2, 'trigger_count': 1},
    ]
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments, triggers=triggers)

    t1 = result['by_turn'][1]
    criatura = t1['categories'][1]
    draw = t1['categories'][2]

    # Each creature event is consumed into draw via resource link
    # total_expected_draw = expected_direct_draw + expected_creature_events
    # using abs=0.02 to account for rounding to 2 decimals
    assert draw['total_expected'] == pytest.approx(draw['expected'] + criatura['expected'], abs=0.02)


def test_joint_probability():
    categories = [
        {'id': 1, 'name': 'ramp', 'color': '#22c55e', 'config': {}},
        {'id': 2, 'name': 'draw', 'color': '#3b82f6', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 3, 'category_id': 2, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments, triggers=[])

    t1 = result['by_turn'][1]
    joint_key = '1_2'
    assert joint_key in t1['joint_probabilities']
    prob = t1['joint_probabilities'][joint_key]
    # P(>=1 ramp AND >=1 draw) should be > 0
    assert prob['P(>=1,1)'] > 0
    assert prob['P(>=1,1)'] < 1.0


def test_max_events():
    categories = [
        {'id': 1, 'name': 'ramp', 'color': '#22c55e', 'config': {}},
        {'id': 2, 'name': 'draw', 'color': '#3b82f6', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 2.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 2, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    triggers = [
        {'source_category_id': 1, 'target_category_id': 2, 'trigger_count': 1},
    ]
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments, triggers=triggers)

    t1 = result['by_turn'][1]
    # Pool for draw = direct_draw + all_ramp (consumed via link)
    # = (7*1/60) + (7*2/60) = 7*3/60 = 0.35
    assert abs(t1['categories'][2]['pool'] - 0.35) < 0.01


def test_prob_at_least_thresholds():
    categories = [{'id': 1, 'name': 'ramp', 'color': '#22c55e', 'config': {}}]
    assignments = [
        {'card_id': i, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None}
        for i in range(10)
    ]
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments, triggers=[])

    t7 = result['by_turn'][7]
    cat_data = t7['categories'][1]
    # With 10 ramps in 60 cards, drawing 13 cards by T7
    # P(>=1) should be high, P(>=3) should be lower
    assert cat_data['prob_at_least_1'] > cat_data['prob_at_least_2']
    assert cat_data['prob_at_least_2'] > cat_data['prob_at_least_3']


def test_multiple_categories_no_triggers():
    categories = [
        {'id': 1, 'name': 'ramp', 'color': '#22c55e', 'config': {}},
        {'id': 2, 'name': 'draw', 'color': '#3b82f6', 'config': {}},
        {'id': 3, 'name': 'alcance', 'color': '#a855f7', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 2, 'multiplier': 2.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 3, 'category_id': 3, 'multiplier': 1.5,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments, triggers=[])

    assert len(result['categories']) == 3
    t1 = result['by_turn'][1]
    assert len(t1['categories']) == 3
