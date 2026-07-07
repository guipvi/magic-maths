from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.deck import Deck, DeckCard
from app.models.card import Card
from app.services.mana_ramp import analyze_mana_ramp, classify_card
from app.services.goldfish import simulate_goldfish
from app.services.interactions import analyze_interactions
from app.services.land_rec import recommend_lands

analysis_bp = Blueprint('analysis', __name__)


def _get_deck_cards(deck_id, user_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return None, None
    deck_cards = []
    for dc in deck.cards.filter_by(is_sideboard=False).all():
        for _ in range(dc.quantity):
            deck_cards.append(dc.card.to_light_dict())
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


@analysis_bp.route('/mana-ramp', methods=['POST'])
@jwt_required()
def mana_ramp():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    if data.get('deck_id'):
        _, cards = _get_deck_cards(data['deck_id'], user_id)
        if cards is None:
            return jsonify({'error': 'Deck not found'}), 404
    elif data.get('cards'):
        cards = _cards_from_payload(data)
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    result = analyze_mana_ramp(cards, deck_size=len(cards))
    return jsonify(result)


@analysis_bp.route('/goldfish', methods=['POST'])
@jwt_required()
def goldfish():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    if data.get('deck_id'):
        _, cards = _get_deck_cards(data['deck_id'], user_id)
        if cards is None:
            return jsonify({'error': 'Deck not found'}), 404
    elif data.get('cards'):
        cards = _cards_from_payload(data)
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    sim_count = data.get('simulations', 2000)
    result = simulate_goldfish(cards, deck_size=len(cards), simulations=sim_count)
    return jsonify(result)


@analysis_bp.route('/interactions', methods=['POST'])
@jwt_required()
def interactions():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    if data.get('deck_id'):
        _, cards = _get_deck_cards(data['deck_id'], user_id)
        if cards is None:
            return jsonify({'error': 'Deck not found'}), 404
    elif data.get('cards'):
        cards = _cards_from_payload(data)
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    result = analyze_interactions(cards)
    return jsonify(result)


@analysis_bp.route('/land-recommendation', methods=['POST'])
@jwt_required()
def land_recommendation():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    if data.get('deck_id'):
        _, cards = _get_deck_cards(data['deck_id'], user_id)
        if cards is None:
            return jsonify({'error': 'Deck not found'}), 404
    elif data.get('cards'):
        cards = _cards_from_payload(data)
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    result = recommend_lands(cards, deck_size=len(cards))
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
    elif data.get('cards'):
        cards = _cards_from_payload(data)
        deck_info = None
    else:
        return jsonify({'error': 'deck_id or cards required'}), 400

    if not cards:
        return jsonify({'error': 'No cards found'}), 400

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as pool:
        mana_future = pool.submit(analyze_mana_ramp, cards, len(cards))
        gold_future = pool.submit(simulate_goldfish, cards, len(cards), 1000)
        int_future = pool.submit(analyze_interactions, cards)
        land_future = pool.submit(recommend_lands, cards, len(cards))

        mana_result = mana_future.result()
        gold_result = gold_future.result()
        int_result = int_future.result()
        land_result = land_future.result()

    return jsonify({
        'deck': deck_info,
        'mana_ramp': mana_result,
        'goldfish': gold_result,
        'interactions': int_result,
        'land_recommendation': land_result,
    })


@analysis_bp.route('/classify-card', methods=['POST'])
@jwt_required()
def classify_card_endpoint():
    data = request.get_json()
    if not data or not data.get('oracle_text'):
        return jsonify({'error': 'oracle_text required'}), 400
    result = classify_card({
        'name': data.get('name', ''),
        'type_line': data.get('type_line', ''),
        'oracle_text': data.get('oracle_text', ''),
        'cmc': data.get('cmc', 0),
    })
    return jsonify(result)
