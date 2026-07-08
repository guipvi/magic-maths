"""
Card model. Stores Scryfall card data; populated on-demand via
services/scryfall.py. Serves as local cache to avoid redundant API calls.
"""
from app.extensions import db


class Card(db.Model):
    __tablename__ = 'cards'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oracle_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    scryfall_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    cmc = db.Column(db.Float, default=0)
    mana_cost = db.Column(db.String(64), default='')
    colors = db.Column(db.JSON, default=list)
    color_identity = db.Column(db.JSON, default=list)
    type_line = db.Column(db.String(256), default='')
    oracle_text = db.Column(db.Text, default='')
    power = db.Column(db.String(16), default='')
    toughness = db.Column(db.String(16), default='')
    rarity = db.Column(db.String(32), default='')
    set_name = db.Column(db.String(128), default='')
    set_code = db.Column(db.String(16), default='')
    prices = db.Column(db.JSON, default=dict)
    image_uris = db.Column(db.JSON, default=dict)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'oracle_id': self.oracle_id,
            'name': self.name,
            'cmc': self.cmc,
            'mana_cost': self.mana_cost,
            'colors': self.colors,
            'color_identity': self.color_identity,
            'type_line': self.type_line,
            'oracle_text': self.oracle_text,
            'power': self.power,
            'toughness': self.toughness,
            'rarity': self.rarity,
            'set_name': self.set_name,
            'set_code': self.set_code,
            'prices': self.prices,
            'image_uris': self.image_uris,
        }

    def to_light_dict(self):
        return {
            'id': self.id,
            'oracle_id': self.oracle_id,
            'name': self.name,
            'cmc': self.cmc,
            'mana_cost': self.mana_cost,
            'colors': self.colors,
            'color_identity': self.color_identity,
            'type_line': self.type_line,
            'oracle_text': self.oracle_text,
            'image_uris': self.image_uris,
        }
