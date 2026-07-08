import uuid
from datetime import datetime, timezone
from app.extensions import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#6366f1')
    config = db.Column(db.JSON, default=dict)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    assignments = db.relationship('DeckCardCategory', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'config': self.config,
            'is_default': self.is_default,
        }


class DeckCardCategory(db.Model):
    __tablename__ = 'deck_card_categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deck_id = db.Column(db.String(36), db.ForeignKey('decks.id'), nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    multiplier = db.Column(db.Float, default=1.0)
    mana_amount = db.Column(db.Integer, nullable=True)
    same_turn = db.Column(db.Boolean, nullable=True)
    is_permanent = db.Column(db.Boolean, nullable=True)
    max_per_turn = db.Column(db.Integer, nullable=True)

    card = db.relationship('Card', backref='category_assignments')

    __table_args__ = (
        db.UniqueConstraint('deck_id', 'card_id', 'category_id', name='uq_deck_card_category'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'deck_id': self.deck_id,
            'card_id': self.card_id,
            'card_name': self.card.name if self.card else None,
            'card_image_uris': self.card.image_uris if self.card else None,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'multiplier': self.multiplier,
            'mana_amount': self.mana_amount,
            'same_turn': self.same_turn,
            'is_permanent': self.is_permanent,
            'max_per_turn': self.max_per_turn,
        }


class DeckCategoryTrigger(db.Model):
    __tablename__ = 'deck_category_triggers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deck_id = db.Column(db.String(36), db.ForeignKey('decks.id'), nullable=False)
    source_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    target_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    trigger_count = db.Column(db.Integer, default=1)
    accumulate = db.Column(db.Boolean, default=False)

    source_category = db.relationship('Category', foreign_keys=[source_category_id])
    target_category = db.relationship('Category', foreign_keys=[target_category_id])

    __table_args__ = (
        db.UniqueConstraint('deck_id', 'source_category_id', 'target_category_id',
                            name='uq_deck_trigger'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'deck_id': self.deck_id,
            'source_category_id': self.source_category_id,
            'source_category_name': self.source_category.name if self.source_category else None,
            'target_category_id': self.target_category_id,
            'target_category_name': self.target_category.name if self.target_category else None,
            'trigger_count': self.trigger_count,
            'accumulate': self.accumulate,
        }


class DeckCardTrigger(db.Model):
    __tablename__ = 'deck_card_triggers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deck_id = db.Column(db.String(36), db.ForeignKey('decks.id'), nullable=False)
    source_assignment_id = db.Column(db.Integer, db.ForeignKey('deck_card_categories.id'),
                                     nullable=False)
    target_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    trigger_count = db.Column(db.Integer, default=1)
    per_turn = db.Column(db.JSON, nullable=True)

    source_assignment = db.relationship('DeckCardCategory',
                                        foreign_keys=[source_assignment_id])
    target_category = db.relationship('Category', foreign_keys=[target_category_id])

    def _resolve_count(self, turn):
        if self.per_turn and isinstance(self.per_turn, list) and len(self.per_turn) >= turn:
            val = self.per_turn[turn - 1]
            if val == -1:
                return self.trigger_count
            return val
        return self.trigger_count

    def to_dict(self):
        return {
            'id': self.id,
            'deck_id': self.deck_id,
            'source_assignment_id': self.source_assignment_id,
            'card_name': self.source_assignment.card.name if self.source_assignment else None,
            'source_category_id': self.source_assignment.category_id if self.source_assignment else None,
            'source_category_name': self.source_assignment.category.name if self.source_assignment else None,
            'target_category_id': self.target_category_id,
            'target_category_name': self.target_category.name if self.target_category else None,
            'trigger_count': self.trigger_count,
            'per_turn': self.per_turn,
        }
