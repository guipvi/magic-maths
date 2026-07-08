import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.deck import Deck, DeckCard
from app.services.scryfall import fetch_or_get_card, fetch_or_get_cards_bulk
from app.utils.card_parser import parse_decklist

logger = logging.getLogger(__name__)
decks_bp = Blueprint('decks', __name__)


@decks_bp.route('', methods=['GET'])
@jwt_required()
def list_decks():
    user_id = get_jwt_identity()
    decks = Deck.query.filter_by(user_id=user_id).order_by(Deck.updated_at.desc()).all()
    return jsonify({'decks': [d.to_dict() for d in decks]})


@decks_bp.route('/<deck_id>', methods=['GET'])
@jwt_required()
def get_deck(deck_id):
    user_id = get_jwt_identity()
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    cards = [dc.to_dict() for dc in deck.cards.order_by(DeckCard.id).all()]
    return jsonify({'deck': deck.to_dict(), 'cards': cards})


@decks_bp.route('', methods=['POST'])
@jwt_required()
def create_deck():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Deck name is required'}), 400

    cards_data = data.get('cards', [])
    names = [item['name'] for item in cards_data if 'name' in item]
    oracle_ids = [item['oracle_id'] for item in cards_data if 'oracle_id' in item]

    card_map = {}
    if names:
        card_map.update(fetch_or_get_cards_bulk(names))
    for oid in oracle_ids:
        card = fetch_or_get_card(oid)
        if card:
            card_map[oid] = card

    resolved_cards = []
    for item in cards_data:
        key = item.get('name') or item.get('oracle_id')
        card = card_map.get(key)
        if card:
            resolved_cards.append((card, item))
        else:
            logger.warning(f'Card not found (skipping): {item.get("name", item.get("oracle_id"))}')

    deck = Deck(
        user_id=user_id,
        name=data['name'],
        format=data.get('format', 'commander'),
        is_public=data.get('is_public', False),
    )
    db.session.add(deck)

    for card, item in resolved_cards:
        dc = DeckCard(
            deck_id=deck.id,
            card_id=card.id,
            quantity=item.get('quantity', 1),
            is_commander=item.get('is_commander', False),
            is_sideboard=item.get('is_sideboard', False),
        )
        db.session.add(dc)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to save deck: {e}')
        return jsonify({'error': 'Failed to save deck'}), 500

    return jsonify({'deck': deck.to_dict()}), 201


@decks_bp.route('/import', methods=['POST'])
@jwt_required()
def import_deck():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data or not data.get('decklist'):
        return jsonify({'error': 'Decklist text is required'}), 400

    parsed = parse_decklist(data['decklist'])

    all_names = list(set(
        [e['name'] for e in parsed['mainboard']] +
        [e['name'] for e in parsed['sideboard']]
    ))
    card_map = fetch_or_get_cards_bulk(all_names)

    merged_main = {}
    for entry in parsed['mainboard']:
        name = entry['name']
        card = card_map.get(name)
        if not card:
            logger.warning(f'Card not found (skipping): {name}')
            continue
        if name in merged_main:
            merged_main[name]['quantity'] += entry['quantity']
            merged_main[name]['is_commander'] = merged_main[name]['is_commander'] or entry.get('is_commander', False)
        else:
            merged_main[name] = entry.copy()

    merged_side = {}
    for entry in parsed['sideboard']:
        name = entry['name']
        card = card_map.get(name)
        if not card:
            logger.warning(f'Card not found (skipping): {name}')
            continue
        if name in merged_side:
            merged_side[name]['quantity'] += entry['quantity']
        else:
            merged_side[name] = entry.copy()

    deck = Deck(
        user_id=user_id,
        name=data.get('name', parsed.get('name', 'Imported Deck')),
        format=data.get('format', parsed.get('format', 'commander')),
    )
    db.session.add(deck)
    db.session.flush()

    for entry in merged_main.values():
        card = card_map[entry['name']]
        dc = DeckCard(
            deck_id=deck.id,
            card_id=card.id,
            quantity=entry['quantity'],
            is_commander=entry.get('is_commander', False),
        )
        db.session.add(dc)

    for entry in merged_side.values():
        card = card_map[entry['name']]
        dc = DeckCard(
            deck_id=deck.id,
            card_id=card.id,
            quantity=entry['quantity'],
            is_sideboard=True,
        )
        db.session.add(dc)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to save imported deck: {e}')
        return jsonify({'error': 'Failed to save deck'}), 500

    return jsonify({'deck': deck.to_dict()}), 201


@decks_bp.route('/<deck_id>', methods=['PUT'])
@jwt_required()
def update_deck(deck_id):
    user_id = get_jwt_identity()
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404

    data = request.get_json()
    if data.get('name'):
        deck.name = data['name']
    if data.get('format'):
        deck.format = data['format']
    if data.get('is_public') is not None:
        deck.is_public = data['is_public']

    if 'cards' in data:
        cards_data = data['cards']
        names = [item['name'] for item in cards_data if 'name' in item]
        oracle_ids = [item['oracle_id'] for item in cards_data if 'oracle_id' in item]

        card_map = {}
        if names:
            card_map.update(fetch_or_get_cards_bulk(names))
        for oid in oracle_ids:
            card = fetch_or_get_card(oid)
            if card:
                card_map[oid] = card

        resolved_cards = []
        for item in cards_data:
            key = item.get('name') or item.get('oracle_id')
            card = card_map.get(key)
            if card:
                resolved_cards.append((card, item))
            else:
                logger.warning(f'Card not found (skipping): {item.get("name", item.get("oracle_id"))}')

        DeckCard.query.filter_by(deck_id=deck.id, is_sideboard=False).delete()
        for card, item in resolved_cards:
            dc = DeckCard(
                deck_id=deck.id,
                card_id=card.id,
                quantity=item.get('quantity', 1),
                is_commander=item.get('is_commander', False),
            )
            db.session.add(dc)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to update deck: {e}')
        return jsonify({'error': 'Failed to update deck'}), 500

    return jsonify({'deck': deck.to_dict()})


@decks_bp.route('/<deck_id>', methods=['DELETE'])
@jwt_required()
def delete_deck(deck_id):
    user_id = get_jwt_identity()
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    db.session.delete(deck)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to delete deck: {e}')
        return jsonify({'error': 'Failed to delete deck'}), 500
    return jsonify({'message': 'Deck deleted'})
