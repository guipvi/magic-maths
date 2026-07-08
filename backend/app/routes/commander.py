from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.deck import Deck, DeckCard
from app.models.card import Card
from app.services.commander_service import (
    get_commander_config, set_commander_config, delete_commander_config,
)
from app.services.scryfall import fetch_or_get_card

commander_bp = Blueprint('commander', __name__)


def _get_deck(deck_id, user_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return None
    return deck


@commander_bp.route('/<deck_id>/commander', methods=['GET'])
@jwt_required()
def get_config(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    config = get_commander_config(deck_id)
    if not config:
        return jsonify({'config': None})
    return jsonify({'config': config.to_dict()})


@commander_bp.route('/<deck_id>/commander', methods=['PUT'])
@jwt_required()
def save_config(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404

    data = request.get_json()
    if not data or not data.get('card_id'):
        return jsonify({'error': 'card_id is required'}), 400

    card_id = data['card_id']
    card = Card.query.get(card_id)
    if not card:
        card = fetch_or_get_card(data.get('card_name', ''))
        if not card:
            return jsonify({'error': 'Card not found'}), 404
        card_id = card.id

    mana_left_over = data.get('mana_left_over', 0)
    min_category_requirements = data.get('min_category_requirements', [])

    # Sync is_commander flag on DeckCard entries
    DeckCard.query.filter_by(deck_id=deck_id, is_commander=True).update({'is_commander': False})
    DeckCard.query.filter_by(deck_id=deck_id, card_id=card_id).update({'is_commander': True})

    config = set_commander_config(
        deck_id=deck_id,
        card_id=card_id,
        mana_left_over=mana_left_over,
        min_category_requirements=min_category_requirements,
    )
    return jsonify({'config': config.to_dict()})


@commander_bp.route('/<deck_id>/commander', methods=['DELETE'])
@jwt_required()
def remove_config(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    if delete_commander_config(deck_id):
        DeckCard.query.filter_by(deck_id=deck_id, is_commander=True).update({'is_commander': False})
        db.session.commit()
        return jsonify({'ok': True})
    return jsonify({'error': 'No commander config found'}), 404
