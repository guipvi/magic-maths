from app.extensions import db
from app.models.category import Category, DeckCardCategory, DeckCategoryTrigger, DeckCardTrigger


DEFAULT_CATEGORIES = [
    {'name': 'ramp', 'color': '#22c55e',
     'config': {'type': 'ramp', 'description': 'Gera mana adicional'}},
    {'name': 'draw', 'color': '#3b82f6',
     'config': {'type': 'draw', 'description': 'Compra cartas'}},
    {'name': 'alcance', 'color': '#a855f7',
     'config': {'type': 'alcance', 'description': 'Draw + scry + filtragem'}},
    {'name': 'destroy', 'color': '#ef4444',
     'config': {'type': 'interaction', 'description': 'Destrói permanentes'}},
    {'name': 'exile', 'color': '#8b5cf6',
     'config': {'type': 'interaction', 'description': 'Exila permanentes'}},
    {'name': 'bounce', 'color': '#38bdf8',
     'config': {'type': 'interaction', 'description': 'Devolve à mão'}},
    {'name': 'counter', 'color': '#6366f1',
     'config': {'type': 'interaction', 'description': 'Anula mágicas'}},
    {'name': 'damage', 'color': '#f97316',
     'config': {'type': 'interaction', 'description': 'Dano a alvos'}},
    {'name': 'graveyard', 'color': '#10b981',
     'config': {'type': 'interaction', 'description': 'Hate ao cemitério'}},
    {'name': 'tuck', 'color': '#fbbf24',
     'config': {'type': 'interaction', 'description': 'Coloca no fundo do grimório'}},
    {'name': 'tutor', 'color': '#ec4899',
     'config': {'type': 'tutor', 'description': 'Busca carta do grimório'}},
]


def seed_default_categories():
    for cat_data in DEFAULT_CATEGORIES:
        existing = Category.query.filter_by(name=cat_data['name']).first()
        if existing:
            if not existing.is_default:
                existing.is_default = True
        else:
            cat = Category(name=cat_data['name'], color=cat_data['color'],
                           config=cat_data['config'], is_default=True)
            db.session.add(cat)
    db.session.commit()


def get_all_categories():
    return Category.query.order_by(Category.name).all()


def get_category(category_id):
    return Category.query.get(category_id)


def create_category(name, color='#6366f1', config=None):
    cat = Category(name=name, color=color, config=config or {})
    db.session.add(cat)
    db.session.commit()
    return cat


def update_category(category_id, **kwargs):
    cat = Category.query.get(category_id)
    if not cat:
        return None
    kwargs.pop('is_default', None)
    for key, value in kwargs.items():
        if hasattr(cat, key):
            setattr(cat, key, value)
    db.session.commit()
    return cat


def delete_category(category_id):
    cat = Category.query.get(category_id)
    if not cat:
        return False
    if cat.is_default:
        return False
    db.session.delete(cat)
    db.session.commit()
    return True


def get_deck_assignments(deck_id):
    return (DeckCardCategory.query
            .filter_by(deck_id=deck_id)
            .order_by(DeckCardCategory.card_id)
            .all())


def set_card_assignment(deck_id, card_id, category_id, multiplier=1.0,
                        mana_amount=None, same_turn=None, is_permanent=None,
                        max_per_turn=None, tutored_card_id=None):
    existing = (DeckCardCategory.query
                .filter_by(deck_id=deck_id, card_id=card_id,
                           category_id=category_id)
                .first())
    if existing:
        existing.multiplier = multiplier
        existing.mana_amount = mana_amount
        existing.same_turn = same_turn
        existing.is_permanent = is_permanent
        existing.max_per_turn = max_per_turn
        existing.tutored_card_id = tutored_card_id
    else:
        assn = DeckCardCategory(
            deck_id=deck_id, card_id=card_id, category_id=category_id,
            multiplier=multiplier, mana_amount=mana_amount,
            same_turn=same_turn, is_permanent=is_permanent,
            max_per_turn=max_per_turn, tutored_card_id=tutored_card_id,
        )
        db.session.add(assn)
    db.session.commit()
    return existing or assn


def remove_card_assignment(assignment_id):
    assn = DeckCardCategory.query.get(assignment_id)
    if not assn:
        return False
    db.session.delete(assn)
    db.session.commit()
    return True


def update_card_assignment(assignment_id, **kwargs):
    assn = DeckCardCategory.query.get(assignment_id)
    if not assn:
        return None
    allowed = ('multiplier', 'mana_amount', 'same_turn', 'is_permanent', 'max_per_turn')
    for key, value in kwargs.items():
        if key in allowed:
            setattr(assn, key, value)
    db.session.commit()
    return assn


def get_deck_triggers(deck_id):
    return (DeckCategoryTrigger.query
            .filter_by(deck_id=deck_id)
            .all())


def set_trigger(deck_id, source_category_id, target_category_id,
                trigger_count=1, accumulate=False):
    existing = (DeckCategoryTrigger.query
                .filter_by(deck_id=deck_id,
                           source_category_id=source_category_id,
                           target_category_id=target_category_id)
                .first())
    if existing:
        existing.trigger_count = trigger_count
        existing.accumulate = accumulate
    else:
        trig = DeckCategoryTrigger(
            deck_id=deck_id,
            source_category_id=source_category_id,
            target_category_id=target_category_id,
            trigger_count=trigger_count,
            accumulate=accumulate,
        )
        db.session.add(trig)
    db.session.commit()
    return existing or trig


def remove_trigger(trigger_id):
    trig = DeckCategoryTrigger.query.get(trigger_id)
    if not trig:
        return False
    db.session.delete(trig)
    db.session.commit()
    return True


# --- DeckCardTrigger CRUD ---

def get_deck_card_triggers(deck_id):
    return (DeckCardTrigger.query
            .filter_by(deck_id=deck_id)
            .all())


def set_card_trigger(deck_id, source_assignment_id, target_category_id,
                     trigger_count=1, per_turn=None):
    existing = (DeckCardTrigger.query
                .filter_by(deck_id=deck_id,
                           source_assignment_id=source_assignment_id,
                           target_category_id=target_category_id)
                .first())
    if existing:
        existing.trigger_count = trigger_count
        existing.per_turn = per_turn
    else:
        trig = DeckCardTrigger(
            deck_id=deck_id,
            source_assignment_id=source_assignment_id,
            target_category_id=target_category_id,
            trigger_count=trigger_count,
            per_turn=per_turn,
        )
        db.session.add(trig)
    db.session.commit()
    return existing or trig


def remove_card_trigger(trigger_id):
    trig = DeckCardTrigger.query.get(trigger_id)
    if not trig:
        return False
    db.session.delete(trig)
    db.session.commit()
    return True
