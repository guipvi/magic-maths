from datetime import datetime, timezone
from app.extensions import db


class PendingTrade(db.Model):
    __tablename__ = 'pending_trades'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deck_id = db.Column(db.String(36), db.ForeignKey('decks.id'), nullable=False)
    card_out_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False)
    card_in_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    planned_assignment = db.Column(db.JSON, nullable=True)
    planned_triggers = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    card_out = db.relationship('Card', foreign_keys=[card_out_id])
    card_in = db.relationship('Card', foreign_keys=[card_in_id])
    deck = db.relationship('Deck', backref='pending_trades')

    def to_dict(self):
        return {
            'id': self.id,
            'deck_id': self.deck_id,
            'card_out': self.card_out.to_light_dict() if self.card_out else None,
            'card_in': self.card_in.to_light_dict() if self.card_in else None,
            'quantity': self.quantity,
            'planned_assignment': self.planned_assignment,
            'planned_triggers': self.planned_triggers,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
