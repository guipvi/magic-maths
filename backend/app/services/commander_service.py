from app.extensions import db
from app.models.deck import DeckCommanderConfig


def get_commander_config(deck_id):
    return DeckCommanderConfig.query.filter_by(deck_id=deck_id).first()


def set_commander_config(deck_id, card_id, mana_left_over=0, min_category_requirements=None):
    config = DeckCommanderConfig.query.filter_by(deck_id=deck_id).first()
    if config:
        config.card_id = card_id
        config.mana_left_over = mana_left_over
        config.min_category_requirements = min_category_requirements or []
    else:
        config = DeckCommanderConfig(
            deck_id=deck_id,
            card_id=card_id,
            mana_left_over=mana_left_over,
            min_category_requirements=min_category_requirements or [],
        )
        db.session.add(config)
    db.session.commit()
    return config


def delete_commander_config(deck_id):
    config = DeckCommanderConfig.query.filter_by(deck_id=deck_id).first()
    if config:
        db.session.delete(config)
        db.session.commit()
        return True
    return False
