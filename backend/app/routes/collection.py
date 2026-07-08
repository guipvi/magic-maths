import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.collection import Collection
from app.models.card import Card
from app.services.scryfall import fetch_or_get_card

logger = logging.getLogger(__name__)
collection_bp = Blueprint('collection', __name__)


@collection_bp.route('', methods=['GET'])
@jwt_required()
def list_collection():
    user_id = get_jwt_identity()
    entries = Collection.query.filter_by(user_id=user_id).order_by(Collection.id).all()
    return jsonify({'collection': [e.to_dict() for e in entries]})


@collection_bp.route('', methods=['POST'])
@jwt_required()
def add_to_collection():
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    card_name = data.get('card_name')
    oracle_id = data.get('oracle_id')
    quantity = data.get('quantity', 1)
    is_foil = data.get('is_foil', False)
    condition = data.get('condition', 'NM')

    if not card_name and not oracle_id:
        return jsonify({'error': 'card_name or oracle_id is required'}), 400

    card = fetch_or_get_card(card_name or oracle_id)
    if not card:
        return jsonify({'error': 'Card not found'}), 404

    try:
        existing = Collection.query.filter_by(
            user_id=user_id, card_id=card.id, is_foil=is_foil
        ).first()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to query collection: {e}')
        return jsonify({'error': 'Database error'}), 500

    if existing:
        existing.quantity += quantity
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f'Failed to update collection: {e}')
            return jsonify({'error': 'Failed to update collection'}), 500
        return jsonify({'collection': existing.to_dict()})

    entry = Collection(
        user_id=user_id,
        card_id=card.id,
        quantity=quantity,
        is_foil=is_foil,
        condition=condition,
    )
    db.session.add(entry)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to add collection entry: {e}')
        return jsonify({'error': 'Failed to add to collection'}), 500
    return jsonify({'collection': entry.to_dict()}), 201


@collection_bp.route('/<entry_id>', methods=['PUT'])
@jwt_required()
def update_entry(entry_id):
    user_id = get_jwt_identity()
    entry = Collection.query.filter_by(id=entry_id, user_id=user_id).first()
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404

    data = request.get_json()
    if data.get('quantity') is not None:
        entry.quantity = data['quantity']
    if data.get('condition'):
        entry.condition = data['condition']
    if data.get('is_foil') is not None:
        entry.is_foil = data['is_foil']

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to update collection entry: {e}')
        return jsonify({'error': 'Failed to update entry'}), 500
    return jsonify({'collection': entry.to_dict()})


@collection_bp.route('/<entry_id>', methods=['DELETE'])
@jwt_required()
def delete_entry(entry_id):
    user_id = get_jwt_identity()
    entry = Collection.query.filter_by(id=entry_id, user_id=user_id).first()
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
    db.session.delete(entry)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to delete collection entry: {e}')
        return jsonify({'error': 'Failed to delete entry'}), 500
    return jsonify({'message': 'Entry deleted'})
