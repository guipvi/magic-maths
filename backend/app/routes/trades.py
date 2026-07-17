import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.deck import Deck, DeckCard
from app.models.pending_trade import PendingTrade
from app.models.collection import Collection
from app.models.category import DeckCardCategory, DeckCardTrigger, DeckAssignmentWaitFor
from app.services.scryfall import fetch_or_get_card

logger = logging.getLogger(__name__)
trades_bp = Blueprint('trades', __name__)


@trades_bp.route('/<deck_id>/trades', methods=['GET'])
@jwt_required()
def list_trades(deck_id):
    user_id = get_jwt_identity()
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404
    trades = PendingTrade.query.filter_by(deck_id=deck_id).order_by(PendingTrade.id).all()
    return jsonify({'trades': [t.to_dict() for t in trades]})


@trades_bp.route('/<deck_id>/trades', methods=['POST'])
@jwt_required()
def create_trade(deck_id):
    user_id = get_jwt_identity()
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    card_out_name = data.get('card_out_name')
    card_in_name = data.get('card_in_name')
    quantity = data.get('quantity', 1)

    if not card_out_name or not card_in_name:
        return jsonify({'error': 'card_out_name and card_in_name are required'}), 400

    card_out = fetch_or_get_card(card_out_name)
    card_in = fetch_or_get_card(card_in_name)

    if not card_out:
        return jsonify({'error': f'Card not found: {card_out_name}'}), 404
    if not card_in:
        return jsonify({'error': f'Card not found: {card_in_name}'}), 404

    trade = PendingTrade(
        deck_id=deck_id,
        card_out_id=card_out.id,
        card_in_id=card_in.id,
        quantity=quantity,
    )
    db.session.add(trade)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to create trade: {e}')
        return jsonify({'error': 'Failed to create trade'}), 500

    return jsonify({'trade': trade.to_dict()}), 201


@trades_bp.route('/<deck_id>/trades/<int:trade_id>', methods=['PUT'])
@jwt_required()
def update_trade(deck_id, trade_id):
    user_id = get_jwt_identity()
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404

    trade = PendingTrade.query.filter_by(id=trade_id, deck_id=deck_id).first()
    if not trade:
        return jsonify({'error': 'Trade not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    if 'planned_assignment' in data:
        trade.planned_assignment = data['planned_assignment']
    if 'planned_triggers' in data:
        trade.planned_triggers = data['planned_triggers']
    if 'quantity' in data:
        trade.quantity = data['quantity']

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to update trade: {e}')
        return jsonify({'error': 'Failed to update trade'}), 500

    return jsonify({'trade': trade.to_dict()})


@trades_bp.route('/<deck_id>/trades/<int:trade_id>', methods=['DELETE'])
@jwt_required()
def delete_trade(deck_id, trade_id):
    user_id = get_jwt_identity()
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404

    trade = PendingTrade.query.filter_by(id=trade_id, deck_id=deck_id).first()
    if not trade:
        return jsonify({'error': 'Trade not found'}), 404

    db.session.delete(trade)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to delete trade: {e}')
        return jsonify({'error': 'Failed to delete trade'}), 500

    return jsonify({'message': 'Trade deleted'})


@trades_bp.route('/<deck_id>/trades/execute', methods=['POST'])
@jwt_required()
def execute_trades(deck_id):
    user_id = get_jwt_identity()
    deck = Deck.query.filter_by(id=deck_id, user_id=user_id).first()
    if not deck:
        return jsonify({'error': 'Deck not found'}), 404

    trades = PendingTrade.query.filter_by(deck_id=deck_id).all()
    if not trades:
        return jsonify({'error': 'No pending trades'}), 400

    executed = []
    errors = []

    for trade in trades:
        try:
            card_out_dc = DeckCard.query.filter_by(
                deck_id=deck_id, card_id=trade.card_out_id, is_sideboard=False
            ).first()

            if not card_out_dc:
                errors.append(f'{trade.card_out.name}: card not found in deck')
                continue

            if card_out_dc.quantity > trade.quantity:
                card_out_dc.quantity -= trade.quantity
            else:
                out_qty = card_out_dc.quantity
                db.session.delete(card_out_dc)

                existing_assignments = DeckCardCategory.query.filter_by(
                    deck_id=deck_id, card_id=trade.card_out_id
                ).all()
                for assn in existing_assignments:
                    triggers = DeckCardTrigger.query.filter_by(
                        source_card_id=trade.card_out_id
                    ).all()
                    for t in triggers:
                        db.session.delete(t)
                    wait_fors = DeckAssignmentWaitFor.query.filter_by(
                        assignment_id=assn.id
                    ).all()
                    for wf in wait_fors:
                        db.session.delete(wf)
                    db.session.delete(assn)

                collection_entry = Collection.query.filter_by(
                    user_id=user_id, card_id=trade.card_out_id, is_foil=False
                ).first()
                if collection_entry:
                    collection_entry.quantity += out_qty
                else:
                    collection_entry = Collection(
                        user_id=user_id,
                        card_id=trade.card_out_id,
                        quantity=out_qty,
                        is_foil=False,
                        condition='NM',
                    )
                    db.session.add(collection_entry)

            card_in_dc = DeckCard.query.filter_by(
                deck_id=deck_id, card_id=trade.card_in_id, is_sideboard=False
            ).first()
            if card_in_dc:
                card_in_dc.quantity += trade.quantity
            else:
                card_in_dc = DeckCard(
                    deck_id=deck_id,
                    card_id=trade.card_in_id,
                    quantity=trade.quantity,
                )
                db.session.add(card_in_dc)

            db.session.flush()

            new_assn_id = None
            if trade.planned_assignment:
                pa = trade.planned_assignment
                new_assn = DeckCardCategory(
                    deck_id=deck_id,
                    card_id=trade.card_in_id,
                    category_id=pa['category_id'],
                    multiplier=pa.get('multiplier', 1.0),
                    mana_amount=pa.get('mana_amount'),
                    same_turn=pa.get('same_turn'),
                    is_permanent=pa.get('is_permanent'),
                    max_per_turn=pa.get('max_per_turn'),
                    tutored_card_id=pa.get('tutored_card_id'),
                    limit_category_id=pa.get('limit_category_id'),
                    limit_only_subsequent=pa.get('limit_only_subsequent', False),
                )
                db.session.add(new_assn)
                db.session.flush()
                new_assn_id = new_assn.id

                wait_for_ids = pa.get('wait_for_category_ids', [])
                for wf_cat_id in wait_for_ids:
                    wf = DeckAssignmentWaitFor(
                        assignment_id=new_assn_id,
                        category_id=wf_cat_id,
                    )
                    db.session.add(wf)

            if trade.planned_triggers:
                for pt in trade.planned_triggers:
                    trigger = DeckCardTrigger(
                        deck_id=deck_id,
                        source_category_id=pt['source_category_id'],
                        source_card_id=pt.get('source_card_id'),
                        target_category_id=pt['target_category_id'],
                        trigger_count=pt.get('trigger_count', 1),
                        per_turn=pt.get('per_turn'),
                        is_permanent=pt.get('is_permanent'),
                        same_turn=pt.get('same_turn'),
                    )
                    db.session.add(trigger)

            executed.append(trade.to_dict())
            db.session.delete(trade)

        except Exception as e:
            logger.error(f'Failed to execute trade {trade.id}: {e}')
            errors.append(f'{trade.card_out.name} → {trade.card_in.name}: {str(e)}')

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Failed to commit trades: {e}')
        return jsonify({'error': 'Failed to execute trades'}), 500

    return jsonify({
        'executed': executed,
        'errors': errors,
        'message': f'{len(executed)} trade(s) executed, {len(errors)} error(s)',
    })
