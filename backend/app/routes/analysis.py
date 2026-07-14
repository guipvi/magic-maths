from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.deck import Deck, DeckCard, DeckCommanderConfig
from app.models.card import Card
from app.models.category import Category, DeckCardCategory, DeckCardTrigger
from app.models.category import DeckCategoryEventLimiter, DeckAssignmentWaitFor
from app.services.mana_ramp import analyze_mana_ramp
from app.services.goldfish import simulate_goldfish
from app.services.interactions import analyze_interactions_from_assignments
from app.services.land_rec import recommend_lands
from app.services.category_analysis import analyze_categories
from app.services.category_service import get_all_categories
from app.services.commander_analysis import analyze_commander_cast


def _run_with_app_context(app, fn, *args, **kwargs):
    with app.app_context():
        return fn(*args, **kwargs)

analysis_bp = Blueprint('analysis', __name__)


def _get_deck_cards(deck_id, user_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return None, None
    deck_cards = []
    for dc in deck.cards.filter_by(is_sideboard=False).all():
        card_dict = dc.card.to_light_dict()
        # Ensure we add 'quantity' to the card dict if needed by some downstream logic, 
        # but the engine expects a list of individual cards expanded by quantity.
        for _ in range(dc.quantity):
            deck_cards.append(card_dict.copy())
    return deck, deck_cards


def _cards_from_payload(data):
    cards = data.get('cards', [])
    result = []
    for c in cards:
        name = c.get('name', '')
        oracle_id = c.get('oracle_id', '')
        card = None
        if oracle_id:
            card = Card.query.filter_by(oracle_id=oracle_id).first()
        if not card and name:
            from app.services.scryfall import fetch_or_get_card
            card = fetch_or_get_card(name)
        if card:
            for _ in range(c.get('quantity', 1)):
                result.append(card.to_light_dict())
    return result


def _load_assignments(deck_id, cards):
    """Load category assignments for a deck, expanded by card quantity."""
    assn_raw = DeckCardCategory.query.filter_by(deck_id=deck_id).all()
    card_counts = {}
    for c in cards:
        cid = c.get('id')
        card_counts[cid] = card_counts.get(cid, 0) + 1

    wait_for_map = {}
    for a in assn_raw:
        wfs = DeckAssignmentWaitFor.query.filter_by(assignment_id=a.id).all()
        if wfs:
            wait_for_map[a.id] = [wf.category_id for wf in wfs]

    assignments = []
    for a in assn_raw:
        for _ in range(card_counts.get(a.card_id, 0)):
            entry = {
                'card_id': a.card_id,
                'category_id': a.category_id,
                'multiplier': a.multiplier,
                'mana_amount': a.mana_amount,
                'same_turn': a.same_turn,
                'is_permanent': a.is_permanent,
                'max_per_turn': a.max_per_turn,
                'limit_category_id': a.limit_category_id,
                'limit_only_subsequent': a.limit_only_subsequent,
            }
            wf = wait_for_map.get(a.id)
            if wf:
                entry['wait_for_category_ids'] = wf
            assignments.append(entry)
    return assignments


def _load_category_data(deck_id, cards):
    """Load categories, card_triggers, limiters, and containment for a deck."""
    from app.services.category_service import build_containment_graph
    all_cats = get_all_categories()
    cat_list = [c.to_dict() for c in all_cats]

    card_trig_raw = DeckCardTrigger.query.filter_by(deck_id=deck_id).all()
    limiter_raw = DeckCategoryEventLimiter.query.filter_by(deck_id=deck_id).all()

    card_counts = {}
    for c in cards:
        cid = c.get('id')
        card_counts[cid] = card_counts.get(cid, 0) + 1

    card_triggers = []
    for ct in card_trig_raw:
        if ct.source_assignment:
            src_cat_id = ct.source_assignment.category_id
            card_id = ct.source_assignment.card_id
            qty = card_counts.get(card_id, 0)
            card_triggers.append({
                'source_card_id': card_id,
                'source_category_id': src_cat_id,
                'target_category_id': ct.target_category_id,
                'trigger_count': ct.trigger_count,
                'quantity': qty,
                'per_turn': ct.per_turn,
            })

    limiters = [l.to_dict() for l in limiter_raw]

    containment_map, _, _, direct_children_of, containment_modes = build_containment_graph()

    return cat_list, card_triggers, limiters, containment_map, direct_children_of, containment_modes


@analysis_bp.route('/mana-ramp', methods=['POST'])
@jwt_required()
def mana_ramp():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    assignments = None
    categories = None
    card_triggers = None
    limiters = None
    containment_map = None
    direct_children_of = None
    containment_modes = None
    if data.get('deck_id'):
        _, cards = _get_deck_cards(data['deck_id'], user_id)
        if cards is None:
            return jsonify({'error': 'Deck not found'}), 404
        assignments = _load_assignments(data['deck_id'], cards)
        categories, card_triggers, limiters, containment_map, direct_children_of, containment_modes = _load_category_data(data['deck_id'], cards)
    elif data.get('cards'):
        cards = _cards_from_payload(data)
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    result = analyze_mana_ramp(cards, deck_size=len(cards), assignments=assignments,
                                categories=categories,
                                card_triggers=card_triggers)
    return jsonify(result)


@analysis_bp.route('/goldfish', methods=['POST'])
@jwt_required()
def goldfish():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    assignments = None
    categories = None
    card_triggers = None
    limiters = None
    containment_map = None
    direct_children_of = None
    containment_modes = None
    if data.get('deck_id'):
        _, cards = _get_deck_cards(data['deck_id'], user_id)
        if cards is None:
            return jsonify({'error': 'Deck not found'}), 404
        assignments = _load_assignments(data['deck_id'], cards)
        categories, card_triggers, limiters, containment_map, direct_children_of, containment_modes = _load_category_data(data['deck_id'], cards)
    elif data.get('cards'):
        cards = _cards_from_payload(data)
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    sim_count = data.get('simulations', 2000)
    result = simulate_goldfish(cards, deck_size=len(cards), simulations=sim_count,
                                assignments=assignments, categories=categories,
                                card_triggers=card_triggers, limiters=limiters,
                                containment_map=containment_map,
                                direct_children_of=direct_children_of,
                                containment_modes=containment_modes)
    return jsonify(result)


@analysis_bp.route('/interactions', methods=['POST'])
@jwt_required()
def interactions():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    if data.get('deck_id'):
        deck, cards = _get_deck_cards(data['deck_id'], user_id)
        if cards is None:
            return jsonify({'error': 'Deck not found'}), 404
        result = analyze_interactions_from_assignments(data['deck_id'], cards)
    elif data.get('cards'):
        cards = _cards_from_payload(data)
        result = {
            'total_interaction_spells': 0,
            'breakdown': {a: {'total': 0, 'by_target': {}} for a in
                          ['destroy', 'exile', 'bounce', 'counter', 'damage', 'graveyard', 'tuck']},
            'spells': [],
            'total_removal': 0,
            'total_counterspells': 0,
            'total_graveyard_hate': 0,
        }
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    return jsonify(result)


@analysis_bp.route('/land-recommendation', methods=['POST'])
@jwt_required()
def land_recommendation():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    assignments = None
    if data.get('deck_id'):
        deck, cards = _get_deck_cards(data['deck_id'], user_id)
        if cards is None:
            return jsonify({'error': 'Deck not found'}), 404
        assignments = _load_assignments(data['deck_id'], cards)
    elif data.get('cards'):
        cards = _cards_from_payload(data)
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    result = recommend_lands(cards, deck_size=len(cards), assignments=assignments)
    return jsonify(result)


@analysis_bp.route('/full', methods=['POST'])
@jwt_required()
def full_analysis():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    if data.get('deck_id'):
        deck, cards = _get_deck_cards(data['deck_id'], user_id)
        if cards is None:
            return jsonify({'error': 'Deck not found'}), 404
        deck_info = deck.to_dict()
        deck_id = data['deck_id']
    elif data.get('cards'):
        cards = _cards_from_payload(data)
        deck_info = None
        deck_id = None
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    from concurrent.futures import ThreadPoolExecutor

    assignments = _load_assignments(deck_id, cards) if deck_id else None
    cat_list = None
    card_triggers = None
    limiters = None
    containment_map = None
    direct_children_of = None
    containment_modes = None
    if deck_id:
        cat_list, card_triggers, limiters, containment_map, direct_children_of, containment_modes = _load_category_data(deck_id, cards)

    app = current_app._get_current_object()

    with ThreadPoolExecutor(max_workers=5) as pool:
        mana_future = pool.submit(
            _run_with_app_context, app, analyze_mana_ramp, cards, len(cards), 5000,
            assignments, cat_list, card_triggers, max_turns=15)
        gold_future = pool.submit(
            _run_with_app_context, app, simulate_goldfish, cards, len(cards), 1000,
            assignments, cat_list, card_triggers, limiters, containment_map,
            direct_children_of, containment_modes)
        land_future = pool.submit(
            _run_with_app_context, app, recommend_lands, cards, len(cards), assignments)

        if deck_id:
            int_future = pool.submit(
                _run_with_app_context, app, analyze_interactions_from_assignments, deck_id, cards)
        else:
            int_future = None

        if cat_list and assignments:
            cat_future = pool.submit(
                _run_with_app_context, app, analyze_categories, len(cards), cat_list,
                assignments, card_triggers=card_triggers, max_turns=15,
                limiters=limiters, containment_map=containment_map,
                direct_children_of=direct_children_of,
                containment_modes=containment_modes)
        else:
            cat_future = None

        mana_result = mana_future.result()
        gold_result = gold_future.result()
        int_result = int_future.result() if int_future else None
        land_result = land_future.result()
        cat_result = cat_future.result() if cat_future else None

    # Commander analysis (depends on mana and category results)
    commander_result = None
    if deck_id:
        comm_config = DeckCommanderConfig.query.filter_by(deck_id=deck_id).first()
        if comm_config and comm_config.card:
            comm_cmc = comm_config.card.cmc or 0
            land_count = len([c for c in cards if 'land' in (c.get('type_line') or '').lower()])

            cat_assignments_for_comm = _load_assignments(deck_id, cards) if assignments else None

            commander_result = analyze_commander_cast(
                deck_size=len(cards),
                commander_cmc=comm_cmc,
                mana_left_over=comm_config.mana_left_over or 0,
                min_category_requirements=comm_config.min_category_requirements or [],
                land_count=land_count,
                category_assignments=cat_assignments_for_comm,
                category_analysis_by_turn=cat_result.get('by_turn') if cat_result else None,
                mana_ramp_by_turn=mana_result.get('by_turn') if mana_result else None,
                condition_groups=comm_config.condition_groups or [],
            )

    # Overwrite category analysis total_expected with mana-gated values for display
    if mana_result and cat_result:
        for turn, mana_turn in mana_result.get('by_turn', {}).items():
            cat_turn = cat_result.get('by_turn', {}).get(turn)
            if cat_turn is None:
                continue
            for cid_str, cat_entry in mana_turn.get('categories', {}).items():
                gated = cat_entry.get('total_expected_gated')
                if gated is not None:
                    cid_int = int(cid_str)
                    if cid_int in cat_turn.get('categories', {}):
                        cat_turn['categories'][cid_int]['total_expected'] = gated

    return jsonify({
        'deck': deck_info,
        'mana_ramp': mana_result,
        'goldfish': gold_result,
        'interactions': int_result,
        'land_recommendation': land_result,
        'categories': cat_result,
        'commander': commander_result,
    })


@analysis_bp.route('/what-if', methods=['POST'])
@jwt_required()
def what_if_analysis():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data or not data.get('deck_id'):
        return jsonify({'error': 'deck_id required'}), 400

    deck_id = data['deck_id']
    deck, cards = _get_deck_cards(deck_id, user_id)
    if cards is None:
        return jsonify({'error': 'Deck not found'}), 404

    from app.models.pending_trade import PendingTrade
    trades = PendingTrade.query.filter_by(deck_id=deck_id).all()
    if not trades:
        return jsonify({'error': 'No pending trades'}), 400

    modified_cards = list(cards)
    traded_out_ids = set()
    for trade in trades:
        out_id = trade.card_out_id
        in_card = trade.card_in.to_light_dict() if trade.card_in else None
        if not in_card:
            continue
        removed = 0
        new_cards = []
        for c in modified_cards:
            if c.get('id') == out_id and removed < trade.quantity:
                removed += 1
                traded_out_ids.add(out_id)
                for _ in range(trade.quantity):
                    new_cards.append(in_card.copy())
            else:
                new_cards.append(c)
        modified_cards = new_cards

    assignments = _load_assignments(deck_id, modified_cards)
    cat_list, card_triggers, limiters, containment_map, direct_children_of, containment_modes = _load_category_data(deck_id, modified_cards)

    assignments = [a for a in assignments if a['card_id'] not in traded_out_ids]
    card_triggers = [ct for ct in card_triggers if ct['source_card_id'] not in traded_out_ids]

    for trade in trades:
        if not trade.planned_assignment or not trade.card_in:
            continue
        pa = trade.planned_assignment
        entry = {
            'card_id': trade.card_in.id,
            'category_id': pa['category_id'],
            'multiplier': pa.get('multiplier', 1.0),
            'mana_amount': pa.get('mana_amount'),
            'same_turn': pa.get('same_turn'),
            'is_permanent': pa.get('is_permanent'),
            'max_per_turn': pa.get('max_per_turn'),
            'tutored_card_id': pa.get('tutored_card_id'),
            'limit_category_id': pa.get('limit_category_id'),
            'limit_only_subsequent': pa.get('limit_only_subsequent', False),
        }
        wf_ids = pa.get('wait_for_category_ids', [])
        if wf_ids:
            entry['wait_for_category_ids'] = wf_ids
        assignments.append(entry)

        if trade.planned_triggers:
            for pt in trade.planned_triggers:
                card_triggers.append({
                    'source_card_id': trade.card_in.id,
                    'source_category_id': pa['category_id'],
                    'target_category_id': pt['target_category_id'],
                    'trigger_count': pt.get('trigger_count', 1),
                    'quantity': trade.quantity,
                    'per_turn': pt.get('per_turn'),
                })

    from concurrent.futures import ThreadPoolExecutor
    app = current_app._get_current_object()

    with ThreadPoolExecutor(max_workers=4) as pool:
        mana_future = pool.submit(
            _run_with_app_context, app, analyze_mana_ramp, modified_cards, len(modified_cards), 5000,
            assignments, cat_list, card_triggers, max_turns=15)
        gold_future = pool.submit(
            _run_with_app_context, app, simulate_goldfish, modified_cards, len(modified_cards), 1000,
            assignments, cat_list, card_triggers, limiters, containment_map,
            direct_children_of, containment_modes)

        if cat_list and assignments:
            cat_future = pool.submit(
                _run_with_app_context, app, analyze_categories, len(modified_cards), cat_list,
                assignments, card_triggers=card_triggers, max_turns=15,
                limiters=limiters, containment_map=containment_map,
                direct_children_of=direct_children_of,
                containment_modes=containment_modes)
        else:
            cat_future = None

        int_future = pool.submit(
            _run_with_app_context, app, analyze_interactions_from_assignments, deck_id, modified_cards)

        mana_result = mana_future.result()
        gold_result = gold_future.result()
        cat_result = cat_future.result() if cat_future else None
        int_result = int_future.result()

    return jsonify({
        'mana_ramp': mana_result,
        'goldfish': gold_result,
        'interactions': int_result,
        'categories': cat_result,
    })


@analysis_bp.route('/categories', methods=['POST'])
@jwt_required()
def categories_analysis():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    if data.get('deck_id'):
        deck, cards = _get_deck_cards(data['deck_id'], user_id)
        if cards is None:
            return jsonify({'error': 'Deck not found'}), 404
        deck_id = data['deck_id']
    elif data.get('cards'):
        cards = _cards_from_payload(data)
        deck_id = None
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    deck_size = len(cards)
    all_categories = get_all_categories()
    cat_list = [c.to_dict() for c in all_categories]

    if deck_id:
        assignments_raw = DeckCardCategory.query.filter_by(deck_id=deck_id).all()
        card_triggers_raw = DeckCardTrigger.query.filter_by(deck_id=deck_id).all()
        limiter_raw = DeckCategoryEventLimiter.query.filter_by(deck_id=deck_id).all()
    else:
        assignments_raw = []
        card_triggers_raw = []
        limiter_raw = []

    assignments = []
    card_counts = {}
    card_map = {}
    for c in cards:
        cid = c.get('id')
        if cid not in card_counts:
            card_counts[cid] = 0
            card_map[cid] = c
        card_counts[cid] += 1

    wait_for_map = {}
    for a in assignments_raw:
        wfs = DeckAssignmentWaitFor.query.filter_by(assignment_id=a.id).all()
        if wfs:
            wait_for_map[a.id] = [wf.category_id for wf in wfs]

    for a in assignments_raw:
        for _ in range(card_counts.get(a.card_id, 0)):
            entry = {
                'card_id': a.card_id,
                'category_id': a.category_id,
                'multiplier': a.multiplier,
                'mana_amount': a.mana_amount,
                'same_turn': a.same_turn,
                'is_permanent': a.is_permanent,
                'max_per_turn': a.max_per_turn,
            }
            wf = wait_for_map.get(a.id)
            if wf:
                entry['wait_for_category_ids'] = wf
            assignments.append(entry)

    card_triggers = []
    for ct in card_triggers_raw:
        if ct.source_assignment:
            src_cat_id = ct.source_assignment.category_id
            card_id = ct.source_assignment.card_id
            qty = card_counts.get(card_id, 0)
            card_triggers.append({
                'source_card_id': card_id,
                'source_category_id': src_cat_id,
                'target_category_id': ct.target_category_id,
                'trigger_count': ct.trigger_count,
                'quantity': qty,
                'per_turn': ct.per_turn,
            })

    limiters = [l.to_dict() for l in limiter_raw]

    containment_map = {}
    direct_children_of = {}
    containment_modes = {}
    if deck_id:
        from app.services.category_service import build_containment_graph
        containment_map, _, _, direct_children_of, containment_modes = build_containment_graph()

    max_turns = data.get('max_turns', 10)
    result = analyze_categories(deck_size, cat_list, assignments, max_turns,
                                card_triggers=card_triggers, limiters=limiters,
                                containment_map=containment_map,
                                direct_children_of=direct_children_of,
                                containment_modes=containment_modes)
    return jsonify(result)
