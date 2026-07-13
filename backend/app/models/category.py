import uuid
from datetime import datetime, timezone
from app.extensions import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64), nullable=False)
    color = db.Column(db.String(7), default='#6366f1')
    config = db.Column(db.JSON, default=dict)
    is_default = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    parent = db.relationship('Category', remote_side='Category.id', backref='children')

    assignments = db.relationship('DeckCardCategory', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'config': self.config,
            'is_default': self.is_default,
            'parent_id': self.parent_id,
        }

    def to_dict_tree(self):
        data = self.to_dict()
        data['children'] = [c.to_dict_tree() for c in sorted(self.children, key=lambda x: x.name)]
        return data


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
    tutored_card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=True)

    card = db.relationship('Card', backref='category_assignments', foreign_keys=[card_id])
    tutored_card = db.relationship('Card', foreign_keys=[tutored_card_id])

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
            'tutored_card_id': self.tutored_card_id,
            'tutored_card_name': self.tutored_card.name if self.tutored_card else None,
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


class DeckCategoryEventLimiter(db.Model):
    __tablename__ = 'deck_category_event_limiters'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deck_id = db.Column(db.String(36), db.ForeignKey('decks.id'), nullable=False)
    target_category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    logic = db.Column(db.String(3), default='OR')
    trigger_count = db.Column(db.Integer, default=1)
    accumulate = db.Column(db.Boolean, default=False)

    target_category = db.relationship('Category', foreign_keys=[target_category_id])
    sources = db.relationship('DeckCategoryEventLimiterSource',
                              backref='limiter', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('deck_id', 'target_category_id',
                            name='uq_deck_limiter'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'deck_id': self.deck_id,
            'target_category_id': self.target_category_id,
            'target_category_name': self.target_category.name if self.target_category else None,
            'logic': self.logic,
            'trigger_count': self.trigger_count,
            'accumulate': self.accumulate,
            'source_category_ids': [s.source_category_id for s in self.sources],
            'source_category_names': [
                s.source_category.name if s.source_category else None
                for s in self.sources
            ],
        }


class DeckCategoryEventLimiterSource(db.Model):
    __tablename__ = 'deck_category_event_limiter_sources'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    limiter_id = db.Column(db.Integer,
                           db.ForeignKey('deck_category_event_limiters.id',
                                         ondelete='CASCADE'),
                           nullable=False)
    source_category_id = db.Column(db.Integer,
                                   db.ForeignKey('categories.id'),
                                   nullable=False)

    source_category = db.relationship('Category',
                                      foreign_keys=[source_category_id])

    __table_args__ = (
        db.UniqueConstraint('limiter_id', 'source_category_id',
                            name='uq_limiter_source'),
    )


class DeckAssignmentWaitFor(db.Model):
    __tablename__ = 'deck_assignment_wait_fors'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    assignment_id = db.Column(db.Integer,
                              db.ForeignKey('deck_card_categories.id',
                                            ondelete='CASCADE'),
                              nullable=False)
    category_id = db.Column(db.Integer,
                            db.ForeignKey('categories.id'),
                            nullable=False)

    category = db.relationship('Category', foreign_keys=[category_id])

    __table_args__ = (
        db.UniqueConstraint('assignment_id', 'category_id',
                            name='uq_assignment_wait_for'),
    )
