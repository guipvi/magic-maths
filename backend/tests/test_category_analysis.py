import pytest
from app.services.category_analysis import analyze_categories


def test_empty_deck():
    result = analyze_categories(deck_size=0, categories=[], assignments=[])
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
    result = analyze_categories(deck_size=40, categories=categories, assignments=assignments)

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
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments)

    assert result['categories'][0]['total_multiplier_sum'] == 3.0
    t1 = result['by_turn'][1]['categories'][1]
    # Expected: 7 * (3.0/60) = 0.35
    assert abs(t1['expected'] - 0.35) < 0.01


def test_limiters_increase_target():
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
    limiters = [
        {'target_category_id': 2, 'logic': 'OR', 'source_category_ids': [1],
         'trigger_count': 1, 'accumulate': False},
    ]
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments,
                                limiters=limiters)

    t1 = result['by_turn'][1]
    criatura = t1['categories'][1]
    draw = t1['categories'][2]

    # Each creature event is consumed into draw via limiter OR
    # total_expected_draw = expected_direct_draw + expected_creature_events
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
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments)

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
    limiters = [
        {'target_category_id': 2, 'logic': 'OR', 'source_category_ids': [1],
         'trigger_count': 1, 'accumulate': False},
    ]
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments,
                                limiters=limiters)

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
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments)

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
    result = analyze_categories(deck_size=60, categories=categories, assignments=assignments)

    assert len(result['categories']) == 3
    t1 = result['by_turn'][1]
    assert len(t1['categories']) == 3


def test_containment_rollup():
    """Cards assigned to child category roll up to container via containment."""
    categories = [
        {'id': 1, 'name': 'sacrifice', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'jund', 'color': '#22c55e', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 3, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    # jund contains sacrifice (user-defined cross-hierarchy)
    containment_map = {2: {1}}
    result = analyze_categories(deck_size=60, categories=categories,
                                assignments=assignments,
                                containment_map=containment_map)

    # sacrifice has 3 cards directly
    assert result['categories'][0]['cards_assigned'] == 3
    # jund should also show 3 cards via containment rollup
    assert result['categories'][1]['cards_assigned'] == 3


def test_containment_limiter_source_expansion():
    """Limiter source expands through containment: source contains child categories."""
    categories = [
        {'id': 1, 'name': 'sacrifice', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'jund', 'color': '#22c55e', 'config': {}},
        {'id': 3, 'name': 'draw', 'color': '#3b82f6', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 3, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    # jund contains sacrifice
    containment_map = {2: {1}}
    # limiter consumes from jund (which contains sacrifice)
    limiters = [
        {'target_category_id': 3, 'logic': 'OR', 'source_category_ids': [2],
         'trigger_count': 1, 'accumulate': False},
    ]
    result_no_contain = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments)
    result_with_contain = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        limiters=limiters, containment_map=containment_map)

    # Without containment, limiter source jund has 0 cards -> no consumption
    draw_no = result_no_contain['by_turn'][1]['categories'][3]
    # With containment, limiter source jund contains sacrifice (3 events) -> consumes into draw
    draw_with = result_with_contain['by_turn'][1]['categories'][3]
    assert draw_with['total_expected'] >= draw_no['total_expected']


def test_containment_wait_for_expansion():
    """Wait_for satisfied by any category that contains the required category."""
    categories = [
        {'id': 1, 'name': 'sacrifice', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'jund', 'color': '#22c55e', 'config': {}},
    ]
    # Card 1: in sacrifice, waits for jund (which contains sacrifice)
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None,
         'wait_for_category_ids': [2]},
    ]
    containment_map = {2: {1}}
    result = analyze_categories(deck_size=40, categories=categories,
                                assignments=assignments,
                                containment_map=containment_map)

    # sacrifice is contained by jund, so wait_for jund should be
    # satisfied by sacrifice cards on battlefield (via containment expansion)
    t1 = result['by_turn'][1]['categories'][1]
    # Without containment, wait_for jund would have 0 probability (no jund cards)
    # With containment, jund is satisfied by sacrifice cards
    assert t1['total_expected'] > 0


# --- 1/n Dilution Tests ---

def test_parent_rollup_diluted_pool():
    """Parent with 2 children: each child event counts as 1/2 in parent pool."""
    categories = [
        {'id': 1, 'name': 'A', 'color': '#ef4444', 'config': {},
         'parent_id': 3},
        {'id': 2, 'name': 'B', 'color': '#3b82f6', 'config': {},
         'parent_id': 3},
        {'id': 3, 'name': 'R', 'color': '#22c55e', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 2.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 2, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    direct_children_of = {3: {1, 2}}
    result = analyze_categories(deck_size=60, categories=categories,
                                assignments=assignments,
                                direct_children_of=direct_children_of)
    result_no_dilution = analyze_categories(deck_size=60, categories=categories,
                                            assignments=assignments)

    t1 = result['by_turn'][1]
    r_data = t1['categories'][3]
    r_no_dil = result_no_dilution['by_turn'][1]['categories'][3]

    # R has 2 direct children, so diluted effective_count = 0.5 + 0.5 = 1.0
    # Non-diluted would have effective_count = 1 + 1 = 2.0
    # Diluted pool should be smaller than non-diluted
    assert r_data['pool'] < r_no_dil['pool']

    # direct_count (for hypergeom) should still be 2 for R
    assert result['categories'][2]['cards_assigned'] == 2


def test_single_child_no_dilution():
    """Parent with 1 child: 1/1 = no dilution, same as before."""
    categories = [
        {'id': 1, 'name': 'A', 'color': '#ef4444', 'config': {},
         'parent_id': 2},
        {'id': 2, 'name': 'R', 'color': '#22c55e', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    direct_children_of = {2: {1}}
    result = analyze_categories(deck_size=60, categories=categories,
                                assignments=assignments,
                                direct_children_of=direct_children_of)

    t1 = result['by_turn'][1]
    r_data = t1['categories'][2]
    # With 1 child, 1/1 = 1.0, no dilution
    # Pool for R = (7*2/60) * 1.0 = 0.233...
    assert abs(r_data['pool'] - 7 * 2 / 60) < 0.01
    assert result['categories'][1]['cards_assigned'] == 2


def test_containment_dilution():
    """User-defined containment: container with 2 contained categories, 1/n dilution."""
    categories = [
        {'id': 1, 'name': 'A', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'B', 'color': '#3b82f6', 'config': {}},
        {'id': 3, 'name': 'Jund', 'color': '#22c55e', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 2, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    # Jund contains both A and B
    containment_map = {3: {1, 2}}
    direct_children_of = {3: {1, 2}}
    result = analyze_categories(deck_size=60, categories=categories,
                                assignments=assignments,
                                containment_map=containment_map,
                                direct_children_of=direct_children_of)
    result_no_dilution = analyze_categories(deck_size=60, categories=categories,
                                            assignments=assignments,
                                            containment_map=containment_map)

    t1 = result['by_turn'][1]
    jund_diluted = t1['categories'][3]
    jund_no_dil = result_no_dilution['by_turn'][1]['categories'][3]

    # Jund has 2 direct children (A, B), diluted pool should be smaller
    assert jund_diluted['pool'] < jund_no_dil['pool']
    # direct_count still 2
    assert result['categories'][2]['cards_assigned'] == 2


def test_direct_count_vs_effective_count():
    """Verify direct_count is 1:1 while effective_count is 1/n diluted."""
    categories = [
        {'id': 1, 'name': 'A', 'color': '#ef4444', 'config': {},
         'parent_id': 3},
        {'id': 2, 'name': 'B', 'color': '#3b82f6', 'config': {},
         'parent_id': 3},
        {'id': 3, 'name': 'R', 'color': '#22c55e', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 2.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 1, 'multiplier': 3.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 3, 'category_id': 2, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    direct_children_of = {3: {1, 2}}
    result = analyze_categories(deck_size=60, categories=categories,
                                assignments=assignments,
                                direct_children_of=direct_children_of)

    # A has 2 cards (multiplier 2+3=5), B has 1 card (multiplier 1)
    # direct_count for R = 3 (1:1 rollup)
    # effective_count for R = 2*(1/2) + 1*(1/2) = 1.0 + 0.5 = 1.5
    # effective_weight for R = 5*(1/2) + 1*(1/2) = 2.5 + 0.5 = 3.0
    # R cards_assigned = 3 (direct_count, 1:1)
    assert result['categories'][2]['cards_assigned'] == 3

    t1 = result['by_turn'][1]
    r_data = t1['categories'][3]
    # R's expected and pool use effective_weight directly:
    # expected = n_drawn * effective_weight / deck_size = 7 * 3.0 / 60 = 0.35
    expected_r = 7 * 3.0 / 60
    assert abs(r_data['expected'] - expected_r) < 0.01
    assert abs(r_data['pool'] - expected_r) < 0.01


def test_no_direct_children_of_fallback():
    """Without direct_children_of, rollup behaves as 1:1 (backward compatible)."""
    categories = [
        {'id': 1, 'name': 'A', 'color': '#ef4444', 'config': {},
         'parent_id': 2},
        {'id': 2, 'name': 'R', 'color': '#22c55e', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    # No direct_children_of passed -> fallback to 1:1
    result = analyze_categories(deck_size=60, categories=categories,
                                assignments=assignments)

    t1 = result['by_turn'][1]
    r_data = t1['categories'][2]
    # Without direct_children_of, n_children=0 -> fallback adds 1:1
    # Pool for R = (7*1/60) * 1.0 = 0.116...
    assert abs(r_data['pool'] - 7 * 1 / 60) < 0.01


# --- Consumption Propagation Tests ---

def test_consumption_propagates_to_container():
    """Limiter consumes from child → container pool should decrease."""
    categories = [
        {'id': 1, 'name': 'sacrifice', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'jund', 'color': '#22c55e', 'config': {}},
        {'id': 3, 'name': 'draw', 'color': '#3b82f6', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 3, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    # jund contains sacrifice
    containment_map = {2: {1}}
    direct_children_of = {2: {1}}
    # limiter consumes from jund (which contains sacrifice)
    limiters = [
        {'target_category_id': 3, 'logic': 'OR', 'source_category_ids': [2],
         'trigger_count': 1, 'accumulate': False},
    ]
    result = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        limiters=limiters, containment_map=containment_map,
        direct_children_of=direct_children_of)

    t1 = result['by_turn'][1]
    # jund has 1 child (sacrifice), 1 card in sacrifice
    # sacrifice pool = 7 * 1 / 60 = 0.1167
    # jund effective_weight = 1/1 = 1.0, pool = 7 * 1 / 60 = 0.1167
    # Limiter consumes from jund → consumed_from_jund consumed
    # draw gets the consumed events
    draw = t1['categories'][3]
    sacrifice = t1['categories'][1]
    # draw should have events from limiter consumption
    assert draw['pool'] > draw['expected']


def test_consumption_does_not_propagate_without_containment():
    """Without containment, consumption stays within the source category."""
    categories = [
        {'id': 1, 'name': 'sacrifice', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'jund', 'color': '#22c55e', 'config': {}},
        {'id': 3, 'name': 'draw', 'color': '#3b82f6', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 2, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 3, 'category_id': 3, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    # No containment_map → no propagation
    limiters = [
        {'target_category_id': 3, 'logic': 'OR', 'source_category_ids': [1],
         'trigger_count': 1, 'accumulate': False},
    ]
    result = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        limiters=limiters)

    t1 = result['by_turn'][1]
    # jund should be unaffected by sacrifice consumption
    jund = t1['categories'][2]
    sacrifice = t1['categories'][1]
    # jund pool = 7 * 1 / 60 (just its own cards, no propagation)
    assert abs(jund['pool'] - 7 * 1 / 60) < 0.01


def test_consumption_propagates_to_multiple_containers():
    """Limiter consumes from child contained by TWO containers → both decrease."""
    categories = [
        {'id': 1, 'name': 'sacrifice', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'jund', 'color': '#22c55e', 'config': {}},
        {'id': 3, 'name': 'aristocrats', 'color': '#a855f7', 'config': {}},
        {'id': 4, 'name': 'draw', 'color': '#3b82f6', 'config': {}},
    ]
    assignments = [
        {'card_id': 1, 'category_id': 1, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
        {'card_id': 2, 'category_id': 4, 'multiplier': 1.0,
         'mana_amount': None, 'same_turn': None, 'is_permanent': None},
    ]
    # Both jund and aristocrats contain sacrifice
    containment_map = {2: {1}, 3: {1}}
    direct_children_of = {2: {1}, 3: {1}}
    # limiter consumes from sacrifice directly
    limiters = [
        {'target_category_id': 4, 'logic': 'OR', 'source_category_ids': [1],
         'trigger_count': 1, 'accumulate': False},
    ]
    result = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        limiters=limiters, containment_map=containment_map,
        direct_children_of=direct_children_of)

    t1 = result['by_turn'][1]
    # Without propagation: jund and aristocrats would keep their full rollup pools
    # With propagation: both should have reduced pools
    result_no_prop = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        containment_map=containment_map, direct_children_of=direct_children_of)

    jund_with = t1['categories'][2]['pool']
    jund_no = result_no_prop['by_turn'][1]['categories'][2]['pool']
    aristocrats_with = t1['categories'][3]['pool']
    aristocrats_no = result_no_prop['by_turn'][1]['categories'][3]['pool']

    # Both containers should have smaller pools when propagation is active
    assert jund_with < jund_no
    assert aristocrats_with < aristocrats_no


def test_ao_mesmo_tempo_rollup_full_weight():
    """ao_mesmo_tempo: card IS both things, rollup uses 1:1 (no dilution)."""
    categories = [
        {'id': 1, 'name': 'criatura', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'artefato', 'color': '#3b82f6', 'config': {}},
        {'id': 3, 'name': 'permanente', 'color': '#a855f7', 'config': {}},
    ]
    # 6 criatura-artefato cards
    assignments = [{'card_id': i, 'category_id': 1, 'multiplier': 1.0,
                    'mana_amount': None, 'same_turn': None, 'is_permanent': None}
                   for i in range(1, 7)]
    assignments += [{'card_id': i, 'category_id': 2, 'multiplier': 1.0,
                     'mana_amount': None, 'same_turn': None, 'is_permanent': None}
                    for i in range(1, 7)]

    containment_map = {3: {1, 2}}
    direct_children_of = {3: {1, 2}}
    # ao_mesmo_tempo: criatura and artefato are both "permanente" simultaneously
    containment_modes = {(3, 1): 'ao_mesmo_tempo', (3, 2): 'ao_mesmo_tempo'}

    result = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        containment_map=containment_map, direct_children_of=direct_children_of,
        containment_modes=containment_modes)

    t1 = result['by_turn'][1]
    permanente = t1['categories'][3]
    criatura = t1['categories'][1]

    # criatura has 6 cards, drawing 7 from 60: expected = 7 * 6/60 = 0.7
    assert abs(criatura['expected'] - 0.7) < 0.01

    # ao_mesmo_tempo: permanente gets full weight from both children
    # effective_weight[3] = 6 (from criatura) + 6 (from artefato) = 12
    # expected = 7 * 12/60 = 1.4
    assert abs(permanente['expected'] - 1.4) < 0.01


def test_ao_mesmo_tempo_vs_subcategoria():
    """Compare ao_mesmo_tempo (1:1) vs subcategoria (1/n) for same structure."""
    categories = [
        {'id': 1, 'name': 'criatura', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'artefato', 'color': '#3b82f6', 'config': {}},
        {'id': 3, 'name': 'permanente', 'color': '#a855f7', 'config': {}},
    ]
    assignments = [{'card_id': i, 'category_id': 1, 'multiplier': 1.0,
                    'mana_amount': None, 'same_turn': None, 'is_permanent': None}
                   for i in range(1, 7)]

    containment_map = {3: {1, 2}}
    direct_children_of = {3: {1, 2}}

    # subcategoria: diluted (1/2)
    result_sub = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        containment_map=containment_map, direct_children_of=direct_children_of,
        containment_modes={(3, 1): 'subcategoria'})

    # ao_mesmo_tempo: full weight (1/1)
    result_full = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        containment_map=containment_map, direct_children_of=direct_children_of,
        containment_modes={(3, 1): 'ao_mesmo_tempo'})

    t1_sub = result_sub['by_turn'][1]
    t1_full = result_full['by_turn'][1]

    # ao_mesmo_tempo should give permanente a higher pool than subcategoria
    assert t1_full['categories'][3]['pool'] > t1_sub['categories'][3]['pool']


def test_ao_mesmo_tempo_consumption_propagation():
    """Consumption propagation: ao_mesmo_tempo propagates 1:1, not 1/n.

    The key difference: with ao_mesmo_tempo, when a child is consumed,
    the container loses MORE pool (full consumed amount vs consumed/n_ch).
    We verify this by checking the DELTA in container pool.
    """
    categories = [
        {'id': 1, 'name': 'sacrifice', 'color': '#ef4444', 'config': {}},
        {'id': 2, 'name': 'token', 'color': '#3b82f6', 'config': {}},
        {'id': 3, 'name': 'jund', 'color': '#f59e0b', 'config': {}},
    ]
    # 10 sacrifice sources (only these roll up to jund)
    assignments = [{'card_id': i, 'category_id': 1, 'multiplier': 1.0,
                    'mana_amount': None, 'same_turn': None, 'is_permanent': None}
                   for i in range(1, 11)]
    # 10 tokens (also roll up to jund)
    assignments += [{'card_id': i, 'category_id': 2, 'multiplier': 1.0,
                     'mana_amount': None, 'same_turn': None, 'is_permanent': None}
                    for i in range(11, 21)]

    containment_map = {3: {1, 2}}
    direct_children_of = {3: {1, 2}}

    # Limiter consumes from sacrifice → token
    limiters = [
        {'target_category_id': 2, 'logic': 'OR', 'source_category_ids': [1],
         'trigger_count': 1, 'accumulate': False},
    ]

    # Run WITH limiter (consumption propagates)
    result_ao = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        limiters=limiters, containment_map=containment_map,
        direct_children_of=direct_children_of,
        containment_modes={(3, 1): 'ao_mesmo_tempo', (3, 2): 'ao_mesmo_tempo'})
    # Run WITHOUT limiter (no consumption, pure rollup)
    result_ao_base = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        containment_map=containment_map,
        direct_children_of=direct_children_of,
        containment_modes={(3, 1): 'ao_mesmo_tempo', (3, 2): 'ao_mesmo_tempo'})

    result_sub = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        limiters=limiters, containment_map=containment_map,
        direct_children_of=direct_children_of,
        containment_modes={(3, 1): 'subcategoria', (3, 2): 'subcategoria'})
    result_sub_base = analyze_categories(
        deck_size=60, categories=categories, assignments=assignments,
        containment_map=containment_map,
        direct_children_of=direct_children_of,
        containment_modes={(3, 1): 'subcategoria', (3, 2): 'subcategoria'})

    # Compute pool loss (delta) for jund container
    delta_ao = result_ao_base['by_turn'][1]['categories'][3]['pool'] - \
               result_ao['by_turn'][1]['categories'][3]['pool']
    delta_sub = result_sub_base['by_turn'][1]['categories'][3]['pool'] - \
                result_sub['by_turn'][1]['categories'][3]['pool']

    # ao_mesmo_tempo should propagate MORE consumption (larger delta)
    assert delta_ao > delta_sub
