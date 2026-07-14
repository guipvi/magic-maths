"""
Deck model. A deck belongs to a user and contains DeckCard entries.
Supports multiple formats (commander, standard, modern, etc.).
Cards can be mainboard, sideboard, or commander zone.
Cascade delete: deleting a Deck removes all DeckCard entries.
"""
import uuid
from datetime import datetime, timezone
from app.extensions import db


class Deck(db.Model):
    __tablename__ = 'decks'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(256), nullable=False)
    format = db.Column(db.String(64), default='commander')
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    cards = db.relationship('DeckCard', backref='deck', lazy='dynamic',
                            cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'format': self.format,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'card_count': sum(c.quantity for c in self.cards.all()),
        }


class DeckCard(db.Model):
    __tablename__ = 'deck_cards'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deck_id = db.Column(db.String(36), db.ForeignKey('decks.id'), nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    is_commander = db.Column(db.Boolean, default=False)
    is_sideboard = db.Column(db.Boolean, default=False)

    card = db.relationship('Card', backref='deck_entries')

    __table_args__ = (
        db.UniqueConstraint('deck_id', 'card_id', 'is_sideboard', name='uq_deck_card'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'deck_id': self.deck_id,
            'card_id': self.card_id,
            'card': self.card.to_light_dict() if self.card else None,
            'quantity': self.quantity,
            'is_commander': self.is_commander,
            'is_sideboard': self.is_sideboard,
        }


class DeckCommanderConfig(db.Model):
    __tablename__ = 'deck_commander_config'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deck_id = db.Column(db.String(36), db.ForeignKey('decks.id'), nullable=False, unique=True)
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False)
    mana_left_over = db.Column(db.Integer, default=0)
    min_category_requirements = db.Column(db.JSON, default=list)  # Legacy: simple list
    condition_groups = db.Column(db.JSON, default=list)  # New: list of condition groups with AND/OR logic
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    deck = db.relationship('Deck', backref=db.backref('commander_config', uselist=False))
    card = db.relationship('Card')

    def to_dict(self):
        return {
            'id': self.id,
            'deck_id': self.deck_id,
            'card_id': self.card_id,
            'card_name': self.card.name if self.card else None,
            'card_cmc': self.card.cmc if self.card else None,
            'card_image_uris': self.card.image_uris if self.card else None,
            'mana_left_over': self.mana_left_over,
            'min_category_requirements': self.min_category_requirements or [],
            'condition_groups': self.condition_groups or [],
        }
