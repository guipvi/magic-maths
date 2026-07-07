"""
Collection model. Links users to cards they own.
Unique constraint: (user_id, card_id, is_foil) — a user can own
both foil and non-foil copies of the same card as separate entries.
"""
from app.extensions import db


class Collection(db.Model):
    __tablename__ = 'collections'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    card_id = db.Column(db.Integer, db.ForeignKey('cards.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    is_foil = db.Column(db.Boolean, default=False)
    condition = db.Column(db.String(16), default='NM')

    card = db.relationship('Card', backref='collection_entries')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'card_id', 'is_foil', name='uq_user_card_foil'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'card': self.card.to_light_dict() if self.card else None,
            'quantity': self.quantity,
            'is_foil': self.is_foil,
            'condition': self.condition,
        }
