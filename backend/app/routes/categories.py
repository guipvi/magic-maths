from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.deck import Deck
from app.models.card import Card
from app.services.category_service import (
    seed_default_categories, get_all_categories, get_category,
    create_category, update_category, delete_category,
    get_deck_assignments, set_card_assignment, remove_card_assignment,
    get_deck_triggers, set_trigger, remove_trigger,
    get_deck_card_triggers, set_card_trigger, remove_card_trigger,
)

categories_bp = Blueprint('categories', __name__)


def _get_deck(deck_id, user_id):
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return None
    return deck


# --- Global Category CRUD ---

@categories_bp.route('', methods=['GET'])
@jwt_required()
def list_categories():
    cats = get_all_categories()
    return jsonify([c.to_dict() for c in cats])


@categories_bp.route('', methods=['POST'])
@jwt_required()
def new_category():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name required'}), 400
    cat = create_category(
        name=data['name'],
        color=data.get('color', '#6366f1'),
        config=data.get('config', {}),
    )
    return jsonify(cat.to_dict()), 201


@categories_bp.route('/<int:category_id>', methods=['PUT'])
@jwt_required()
def edit_category(category_id):
    data = request.get_json()
    cat = update_category(category_id, **{k: v for k, v in data.items()
                                         if k in ('name', 'color', 'config')})
    if not cat:
        return jsonify({'error': 'Category not found'}), 404
    return jsonify(cat.to_dict())


@categories_bp.route('/<int:category_id>', methods=['DELETE'])
@jwt_required()
def remove_category(category_id):
    from app.models.category import Category
    cat = Category.query.get(category_id)
    if not cat:
        return jsonify({'error': 'Category not found'}), 404
    if cat.is_default:
        return jsonify({'error': 'Cannot delete default category'}), 400
    if delete_category(category_id):
        return jsonify({'ok': True})
    return jsonify({'error': 'Category not found'}), 404


# --- Card-Category Assignments per deck ---

@categories_bp.route('/deck/<deck_id>/assignments', methods=['GET'])
@jwt_required()
def list_assignments(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    assignments = get_deck_assignments(deck_id)
    return jsonify([a.to_dict() for a in assignments])


@categories_bp.route('/deck/<deck_id>/assignments', methods=['POST'])
@jwt_required()
def add_assignment(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    data = request.get_json()
    if not data or not data.get('card_id') or not data.get('category_id'):
        return jsonify({'error': 'card_id and category_id required'}), 400
    assn = set_card_assignment(
        deck_id=deck_id,
        card_id=data['card_id'],
        category_id=data['category_id'],
        multiplier=data.get('multiplier', 1.0),
        mana_amount=data.get('mana_amount'),
        same_turn=data.get('same_turn'),
        is_permanent=data.get('is_permanent'),
        max_per_turn=data.get('max_per_turn'),
    )
    return jsonify(assn.to_dict()), 201


@categories_bp.route('/deck/<deck_id>/assignments/<int:assignment_id>', methods=['DELETE'])
@jwt_required()
def delete_assignment(deck_id, assignment_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    if remove_card_assignment(assignment_id):
        return jsonify({'ok': True})
    return jsonify({'error': 'Assignment not found'}), 404


# --- Triggers per deck ---

@categories_bp.route('/deck/<deck_id>/triggers', methods=['GET'])
@jwt_required()
def list_triggers(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    triggers = get_deck_triggers(deck_id)
    return jsonify([t.to_dict() for t in triggers])


@categories_bp.route('/deck/<deck_id>/triggers', methods=['POST'])
@jwt_required()
def add_trigger(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    data = request.get_json()
    if not data or not data.get('source_category_id') or not data.get('target_category_id'):
        return jsonify({'error': 'source_category_id and target_category_id required'}), 400
    trig = set_trigger(
        deck_id=deck_id,
        source_category_id=data['source_category_id'],
        target_category_id=data['target_category_id'],
        trigger_count=data.get('trigger_count', 1),
        accumulate=data.get('accumulate', False),
    )
    return jsonify(trig.to_dict()), 201


@categories_bp.route('/deck/<deck_id>/triggers/<int:trigger_id>', methods=['DELETE'])
@jwt_required()
def delete_trigger(deck_id, trigger_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    if remove_trigger(trigger_id):
        return jsonify({'ok': True})
    return jsonify({'error': 'Trigger not found'}), 404


# --- Card-Trigger per deck ---

@categories_bp.route('/deck/<deck_id>/card-triggers', methods=['GET'])
@jwt_required()
def list_card_triggers(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    triggers = get_deck_card_triggers(deck_id)
    return jsonify([t.to_dict() for t in triggers])


@categories_bp.route('/deck/<deck_id>/card-triggers', methods=['POST'])
@jwt_required()
def add_card_trigger(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    data = request.get_json()
    if not data or not data.get('source_assignment_id') or not data.get('target_category_id'):
        return jsonify({'error': 'source_assignment_id and target_category_id required'}), 400
    trig = set_card_trigger(
        deck_id=deck_id,
        source_assignment_id=data['source_assignment_id'],
        target_category_id=data['target_category_id'],
        trigger_count=data.get('trigger_count', 1),
        per_turn=data.get('per_turn'),
    )
    return jsonify(trig.to_dict()), 201


@categories_bp.route('/deck/<deck_id>/card-triggers/<int:trigger_id>', methods=['DELETE'])
@jwt_required()
def delete_card_trigger(deck_id, trigger_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    if remove_card_trigger(trigger_id):
        return jsonify({'ok': True})
    return jsonify({'error': 'Card trigger not found'}), 404
