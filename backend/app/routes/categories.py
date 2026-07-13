from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.deck import Deck
from app.models.card import Card
from app.services.category_service import (
    seed_default_categories, get_all_categories, get_category,
    get_category_tree, create_category, update_category, delete_category,
    get_deck_assignments, set_card_assignment, remove_card_assignment,
    get_deck_card_triggers, set_card_trigger, remove_card_trigger,
    get_deck_limiters, set_limiter, remove_limiter,
    set_assignment_wait_fors,
    build_containment_graph, get_containment_edges, add_containment,
    remove_containment,
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


@categories_bp.route('/tree', methods=['GET'])
@jwt_required()
def list_category_tree():
    tree = get_category_tree()
    return jsonify(tree)


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
        parent_id=data.get('parent_id'),
    )
    return jsonify(cat.to_dict()), 201


@categories_bp.route('/<int:category_id>', methods=['PUT'])
@jwt_required()
def edit_category(category_id):
    data = request.get_json()
    allowed = ('name', 'color', 'config', 'parent_id')
    cat = update_category(category_id, **{k: v for k, v in data.items()
                                         if k in allowed})
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
    result = delete_category(category_id)
    if result is None:
        return jsonify({'error': 'Cannot delete category with subcategories'}), 400
    if result:
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
        tutored_card_id=data.get('tutored_card_id'),
        wait_for_category_ids=data.get('wait_for_category_ids'),
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


# --- Event Limiters per deck ---

@categories_bp.route('/deck/<deck_id>/limiters', methods=['GET'])
@jwt_required()
def list_limiters(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    limiters = get_deck_limiters(deck_id)
    return jsonify([l.to_dict() for l in limiters])


@categories_bp.route('/deck/<deck_id>/limiters', methods=['POST'])
@jwt_required()
def add_limiter(deck_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    data = request.get_json()
    if not data or not data.get('target_category_id') or not data.get('source_category_ids'):
        return jsonify({'error': 'target_category_id and source_category_ids required'}), 400
    limiter = set_limiter(
        deck_id=deck_id,
        target_category_id=data['target_category_id'],
        source_category_ids=data['source_category_ids'],
        logic=data.get('logic', 'OR'),
        trigger_count=data.get('trigger_count', 1),
        accumulate=data.get('accumulate', False),
    )
    return jsonify(limiter.to_dict()), 201


@categories_bp.route('/deck/<deck_id>/limiters/<int:limiter_id>', methods=['DELETE'])
@jwt_required()
def delete_limiter(deck_id, limiter_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    if remove_limiter(limiter_id):
        return jsonify({'ok': True})
    return jsonify({'error': 'Limiter not found'}), 404


# --- Wait-for per assignment ---

@categories_bp.route('/deck/<deck_id>/assignments/<int:assignment_id>/wait-for', methods=['POST'])
@jwt_required()
def set_wait_for(deck_id, assignment_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    data = request.get_json()
    if data is None or 'category_ids' not in data:
        return jsonify({'error': 'category_ids required'}), 400
    set_assignment_wait_fors(assignment_id, data['category_ids'])
    return jsonify({'ok': True})


@categories_bp.route('/deck/<deck_id>/assignments/<int:assignment_id>/wait-for', methods=['GET'])
@jwt_required()
def get_wait_for(deck_id, assignment_id):
    user_id = get_jwt_identity()
    deck = _get_deck(deck_id, user_id)
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    from app.services.category_service import get_assignment_wait_fors
    wait_fors = get_assignment_wait_fors(assignment_id)
    return jsonify([{
        'id': wf.id,
        'category_id': wf.category_id,
        'category_name': wf.category.name if wf.category else None,
    } for wf in wait_fors])


# --- Category Containment ---

@categories_bp.route('/containment', methods=['GET'])
@jwt_required()
def list_containment():
    edges = get_containment_edges()
    return jsonify(edges)


@categories_bp.route('/containment', methods=['POST'])
@jwt_required()
def create_containment():
    data = request.get_json()
    if not data or not data.get('container_category_id') or not data.get('contained_category_id'):
        return jsonify({'error': 'container_category_id and contained_category_id required'}), 400
    try:
        edge = add_containment(
            data['container_category_id'],
            data['contained_category_id'],
        )
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    return jsonify({
        'id': edge.id,
        'container_category_id': edge.container_category_id,
        'contained_category_id': edge.contained_category_id,
    }), 201


@categories_bp.route('/containment/<int:containment_id>', methods=['DELETE'])
@jwt_required()
def delete_containment(containment_id):
    if remove_containment(containment_id):
        return jsonify({'ok': True})
    return jsonify({'error': 'Containment not found'}), 404
