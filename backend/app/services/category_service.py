from collections import defaultdict
from app.extensions import db
from app.models.category import (Category, DeckCardCategory,
                                  DeckCardTrigger, DeckCategoryEventLimiter,
                                  DeckCategoryEventLimiterSource, DeckAssignmentWaitFor,
                                  CategoryContainment)


DEFAULT_CATEGORIES = [
    {'name': 'ramp', 'color': '#22c55e',
     'config': {'type': 'ramp', 'description': 'Gera mana adicional'}},
    {'name': 'draw', 'color': '#3b82f6',
     'config': {'type': 'draw', 'description': 'Compra cartas'}},
    {'name': 'alcance', 'color': '#a855f7',
     'config': {'type': 'alcance', 'description': 'Draw + scry + filtragem'}},
    {'name': 'tutor', 'color': '#ec4899',
     'config': {'type': 'tutor', 'description': 'Busca carta do grimório'}},
    # Interaction categories (root, with subcategories for target types)
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
    {'name': 'graveyard hate', 'color': '#10b981',
     'config': {'type': 'interaction', 'description': 'Hate ao cemitério'}},
    {'name': 'tuck', 'color': '#fbbf24',
     'config': {'type': 'interaction', 'description': 'Coloca no fundo do grimório'}},
]

DEFAULT_SUBCATEGORIES: list[dict] = [
    # destroy targets
    {'name': 'permanente', 'parent_name': 'destroy', 'color': '#fca5a5',
     'config': {'type': 'destroy', 'description': 'Qualquer permanente'}},
    {'name': 'não-criatura', 'parent_name': 'destroy', 'color': '#f87171',
     'config': {'type': 'destroy', 'description': 'Permanente que não seja criatura'}},
    {'name': 'criatura', 'parent_name': 'destroy', 'color': '#ef4444',
     'config': {'type': 'destroy', 'description': 'Criatura'}},
    # exile targets
    {'name': 'permanente', 'parent_name': 'exile', 'color': '#c4b5fd',
     'config': {'type': 'exile', 'description': 'Qualquer permanente'}},
    {'name': 'não-criatura', 'parent_name': 'exile', 'color': '#a78bfa',
     'config': {'type': 'exile', 'description': 'Permanente que não seja criatura'}},
    {'name': 'criatura', 'parent_name': 'exile', 'color': '#8b5cf6',
     'config': {'type': 'exile', 'description': 'Criatura'}},
    {'name': 'cemitério', 'parent_name': 'exile', 'color': '#7c3aed',
     'config': {'type': 'exile', 'description': 'Exila do cemitério'}},
    # bounce targets
    {'name': 'não-terreno', 'parent_name': 'bounce', 'color': '#7dd3fc',
     'config': {'type': 'bounce', 'description': 'Permanente que não seja terreno'}},
    {'name': 'criatura', 'parent_name': 'bounce', 'color': '#38bdf8',
     'config': {'type': 'bounce', 'description': 'Criatura'}},
    # counter targets
    {'name': 'mágica', 'parent_name': 'counter', 'color': '#a5b4fc',
     'config': {'type': 'counter', 'description': 'Qualquer mágica'}},
    {'name': 'não-criatura', 'parent_name': 'counter', 'color': '#818cf8',
     'config': {'type': 'counter', 'description': 'Mágica que não seja criatura'}},
    # damage targets
    {'name': 'qualquer', 'parent_name': 'damage', 'color': '#fdba74',
     'config': {'type': 'damage', 'description': 'Qualquer alvo'}},
    {'name': 'criatura', 'parent_name': 'damage', 'color': '#f97316',
     'config': {'type': 'damage', 'description': 'Criatura'}},
    {'name': 'planeswalker', 'parent_name': 'damage', 'color': '#ea580c',
     'config': {'type': 'damage', 'description': 'Planeswalker'}},
    # graveyard hate targets
    {'name': 'cemitério', 'parent_name': 'graveyard hate', 'color': '#34d399',
     'config': {'type': 'graveyard hate', 'description': 'Cemitério'}},
    # tuck targets
    {'name': 'qualquer', 'parent_name': 'tuck', 'color': '#fde68a',
     'config': {'type': 'tuck', 'description': 'Qualquer alvo'}},
    {'name': 'não-terreno', 'parent_name': 'tuck', 'color': '#fbbf24',
     'config': {'type': 'tuck', 'description': 'Permanente que não seja terreno'}},
]


def _migrate_add_card_ids_filter():
    """Add card_ids_filter column to deck_category_event_limiter_sources if missing."""
    from sqlalchemy import text, inspect as sa_inspect
    inspector = sa_inspect(db.engine)
    if 'deck_category_event_limiter_sources' not in inspector.get_table_names():
        return
    columns = {col['name'] for col in inspector.get_columns('deck_category_event_limiter_sources')}
    if 'card_ids_filter' not in columns:
        db.session.execute(text(
            'ALTER TABLE deck_category_event_limiter_sources '
            'ADD COLUMN card_ids_filter TEXT'
        ))
        db.session.commit()


def _migrate_add_assignment_limit():
    """Add limit_category_id and limit_only_subsequent to deck_card_categories if missing."""
    from sqlalchemy import text, inspect as sa_inspect
    inspector = sa_inspect(db.engine)
    if 'deck_card_categories' not in inspector.get_table_names():
        return
    columns = {col['name'] for col in inspector.get_columns('deck_card_categories')}
    if 'limit_category_id' not in columns:
        db.session.execute(text(
            'ALTER TABLE deck_card_categories '
            'ADD COLUMN limit_category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL'
        ))
        db.session.commit()
    if 'limit_only_subsequent' not in columns:
        db.session.execute(text(
            'ALTER TABLE deck_card_categories '
            'ADD COLUMN limit_only_subsequent BOOLEAN DEFAULT 0'
        ))
        db.session.commit()


def seed_default_categories():
    # Migration: clear parent_id and is_default from old "interaction" parent
    old_interaction = Category.query.filter_by(name='interaction', is_default=True).first()
    if old_interaction:
        for child in old_interaction.children[:]:
            child.parent_id = None
        db.session.delete(old_interaction)

    # Migration: rename "graveyard" -> "graveyard hate" if old name exists
    old_gy = Category.query.filter_by(name='graveyard').first()
    if old_gy:
        if not Category.query.filter_by(name='graveyard hate').first():
            old_gy.name = 'graveyard hate'
            old_gy.config = {'type': 'interaction', 'description': 'Hate ao cemitério'}
        else:
            # "graveyard hate" already exists — move any assignments to it
            existing_gy_hate = Category.query.filter_by(name='graveyard hate').first()
            for child in old_gy.children[:]:
                child.parent_id = existing_gy_hate.id
            db.session.delete(old_gy)

    for cat_data in DEFAULT_CATEGORIES:
        existing = Category.query.filter_by(name=cat_data['name']).first()
        if existing:
            if not existing.is_default:
                existing.is_default = True
            existing.parent_id = None  # ensure root
        else:
            cat = Category(name=cat_data['name'], color=cat_data['color'],
                           config=cat_data['config'], is_default=True)
            db.session.add(cat)
    db.session.flush()

    for sub_data in DEFAULT_SUBCATEGORIES:
        parent = Category.query.filter_by(name=sub_data['parent_name']).first()
        if not parent:
            continue
        existing = Category.query.filter_by(name=sub_data['name'], parent_id=parent.id).first()
        if existing:
            existing.config = sub_data['config']
            existing.color = sub_data['color']
            existing.is_default = True
        else:
            cat = Category(name=sub_data['name'], color=sub_data['color'],
                           config=sub_data['config'], is_default=True,
                           parent_id=parent.id)
            db.session.add(cat)
    db.session.commit()

    _migrate_triggers_to_limiters()
    _migrate_add_card_ids_filter()
    _migrate_add_assignment_limit()


def _migrate_triggers_to_limiters():
    """Migrate DeckCategoryTrigger entries to DeckCategoryEventLimiter (OR, 1 source).

    Called on startup. Uses raw SQL to read from the old table and insert into
    the new tables, since the ORM model no longer exists.
    """
    from sqlalchemy import text, inspect as sa_inspect
    inspector = sa_inspect(db.engine)
    if 'deck_category_triggers' not in inspector.get_table_names():
        return

    rows = db.session.execute(
        text('SELECT deck_id, source_category_id, target_category_id, '
             'trigger_count, accumulate FROM deck_category_triggers')
    ).fetchall()

    if not rows:
        db.session.execute(text('DROP TABLE deck_category_triggers'))
        db.session.commit()
        return

    for deck_id, src_id, tgt_id, count, accumulate in rows:
        existing = db.session.execute(
            text('SELECT id FROM deck_category_event_limiters '
                 'WHERE deck_id = :did AND target_category_id = :tgt'),
            {'did': deck_id, 'tgt': tgt_id}
        ).fetchone()

        if existing:
            lim_id = existing[0]
            db.session.execute(
                text('UPDATE deck_category_event_limiters SET logic = :logic, '
                     'trigger_count = :tc, accumulate = :acc WHERE id = :id'),
                {'logic': 'OR', 'tc': count, 'acc': accumulate, 'id': lim_id}
            )
        else:
            db.session.execute(
                text('INSERT INTO deck_category_event_limiters '
                     '(deck_id, target_category_id, logic, trigger_count, accumulate) '
                     'VALUES (:did, :tgt, :logic, :tc, :acc)'),
                {'did': deck_id, 'tgt': tgt_id, 'logic': 'OR', 'tc': count, 'acc': accumulate}
            )
            lim_id = db.session.execute(text('SELECT last_insert_rowid()')).scalar()

        db.session.execute(
            text('INSERT OR IGNORE INTO deck_category_event_limiter_sources '
                 '(limiter_id, source_category_id) VALUES (:lid, :sid)'),
            {'lid': lim_id, 'sid': src_id}
        )

    db.session.execute(text('DROP TABLE deck_category_triggers'))
    db.session.commit()


def get_all_categories():
    return Category.query.order_by(Category.name).all()


def get_category(category_id):
    return Category.query.get(category_id)


def get_category_tree():
    """Return categories organized as a tree (roots with nested children)."""
    roots = Category.query.filter_by(parent_id=None).order_by(Category.name).all()
    return [r.to_dict_tree() for r in roots]


def get_root_categories():
    return Category.query.filter_by(parent_id=None).order_by(Category.name).all()


def get_child_categories(parent_id):
    return Category.query.filter_by(parent_id=parent_id).order_by(Category.name).all()


def create_category(name, color='#6366f1', config=None, parent_id=None):
    cat = Category(name=name, color=color, config=config or {}, parent_id=parent_id)
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
    if cat.children:
        return None  # signal: has children, can't delete

    from app.models.category import (
        DeckCardCategory, DeckCardTrigger, DeckCategoryEventLimiter,
        DeckCategoryEventLimiterSource, DeckAssignmentWaitFor,
        CategoryContainment,
    )

    DeckAssignmentWaitFor.query.filter_by(category_id=category_id).delete(synchronize_session='fetch')
    DeckCategoryEventLimiterSource.query.filter_by(source_category_id=category_id).delete(synchronize_session='fetch')
    DeckCategoryEventLimiter.query.filter_by(target_category_id=category_id).delete(synchronize_session='fetch')
    DeckCardTrigger.query.filter_by(target_category_id=category_id).delete(synchronize_session='fetch')
    DeckCardCategory.query.filter_by(category_id=category_id).delete(synchronize_session='fetch')
    CategoryContainment.query.filter(
        (CategoryContainment.container_category_id == category_id) |
        (CategoryContainment.contained_category_id == category_id)
    ).delete(synchronize_session='fetch')

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
                        max_per_turn=None, tutored_card_id=None,
                        wait_for_category_ids=None,
                        limit_category_id=None, limit_only_subsequent=None):
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
        existing.limit_category_id = limit_category_id
        existing.limit_only_subsequent = limit_only_subsequent or False
        assn = existing
    else:
        assn = DeckCardCategory(
            deck_id=deck_id, card_id=card_id, category_id=category_id,
            multiplier=multiplier, mana_amount=mana_amount,
            same_turn=same_turn, is_permanent=is_permanent,
            max_per_turn=max_per_turn, tutored_card_id=tutored_card_id,
            limit_category_id=limit_category_id,
            limit_only_subsequent=limit_only_subsequent or False,
        )
        db.session.add(assn)
    db.session.flush()

    if wait_for_category_ids is not None:
        DeckAssignmentWaitFor.query.filter_by(assignment_id=assn.id).delete()
        for cat_id in wait_for_category_ids:
            db.session.add(DeckAssignmentWaitFor(
                assignment_id=assn.id, category_id=cat_id))

    db.session.commit()
    return assn


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


# --- DeckCategoryEventLimiter CRUD ---

def get_deck_limiters(deck_id):
    return (DeckCategoryEventLimiter.query
            .filter_by(deck_id=deck_id)
            .all())


def set_limiter(deck_id, target_category_id, source_category_ids,
                logic='OR', trigger_count=1, accumulate=False,
                source_card_filters=None):
    existing = (DeckCategoryEventLimiter.query
                .filter_by(deck_id=deck_id,
                           target_category_id=target_category_id)
                .first())
    if existing:
        existing.logic = logic
        existing.trigger_count = trigger_count
        existing.accumulate = accumulate
        DeckCategoryEventLimiterSource.query.filter_by(
            limiter_id=existing.id).delete()
        limiter = existing
    else:
        limiter = DeckCategoryEventLimiter(
            deck_id=deck_id,
            target_category_id=target_category_id,
            logic=logic,
            trigger_count=trigger_count,
            accumulate=accumulate,
        )
        db.session.add(limiter)
    db.session.flush()

    filters = source_card_filters or {}
    for src_cat_id in source_category_ids:
        card_filter = filters.get(src_cat_id)
        db.session.add(DeckCategoryEventLimiterSource(
            limiter_id=limiter.id,
            source_category_id=src_cat_id,
            card_ids_filter=card_filter if card_filter else None,
        ))

    db.session.commit()
    return limiter


def remove_limiter(limiter_id):
    limiter = DeckCategoryEventLimiter.query.get(limiter_id)
    if not limiter:
        return False
    db.session.delete(limiter)
    db.session.commit()
    return True


def update_limiter_source_card_filter(limiter_id, source_category_id, card_ids_filter):
    source = DeckCategoryEventLimiterSource.query.filter_by(
        limiter_id=limiter_id,
        source_category_id=source_category_id).first()
    if not source:
        return None
    source.card_ids_filter = card_ids_filter if card_ids_filter else None
    db.session.commit()
    return source


# --- DeckAssignmentWaitFor CRUD ---

def get_assignment_wait_fors(assignment_id):
    return (DeckAssignmentWaitFor.query
            .filter_by(assignment_id=assignment_id)
            .all())


def set_assignment_wait_fors(assignment_id, category_ids):
    DeckAssignmentWaitFor.query.filter_by(
        assignment_id=assignment_id).delete()
    for cat_id in category_ids:
        db.session.add(DeckAssignmentWaitFor(
            assignment_id=assignment_id,
            category_id=cat_id,
        ))
    db.session.commit()


# --- Category Containment ---

def build_containment_graph():
    """Build transitive closure of containment.

    Combines two sources:
      1. Parent-child hierarchy (parent contains child, transitive)
      2. User-defined CategoryContainment rows

    Returns:
        contains_map: {cat_id: set of all cat_ids that it contains}
        contained_by_map: {cat_id: set of all cat_ids that contain it}
        direct_contains: {cat_id: set of directly contained cat_ids (user-defined only)}
        direct_children_of: {cat_id: set of direct children (parent-child + user-defined)}
        containment_modes: {(container_id, contained_id): mode} for user-defined edges
    """
    all_cats = Category.query.all()
    cat_ids = [c.id for c in all_cats]

    # Build adjacency from parent-child: parent contains child
    children_of = defaultdict(set)
    for c in all_cats:
        if c.parent_id is not None:
            children_of[c.parent_id].add(c.id)

    # Build adjacency from user-defined containment
    containment_rows = CategoryContainment.query.all()
    user_edges = defaultdict(set)
    containment_modes = {}
    for row in containment_rows:
        user_edges[row.container_category_id].add(row.contained_category_id)
        containment_modes[(row.container_category_id, row.contained_category_id)] = row.mode or 'subcategoria'

    # Merge into single adjacency list
    forward = defaultdict(set)
    for pid, cids in children_of.items():
        forward[pid].update(cids)
    for pid, cids in user_edges.items():
        forward[pid].update(cids)

    # Compute transitive closure via BFS from each node
    contains_map = {}
    for start in cat_ids:
        visited = set()
        queue = [start]
        while queue:
            node = queue.pop(0)
            for nxt in forward.get(node, []):
                if nxt not in visited and nxt != start:
                    visited.add(nxt)
                    queue.append(nxt)
        contains_map[start] = visited

    # Invert for contained_by_map
    contained_by_map = defaultdict(set)
    for cid, contained_set in contains_map.items():
        for inner in contained_set:
            contained_by_map[inner].add(cid)

    # Only user-defined direct edges (for display/API)
    direct_contains = defaultdict(set)
    for row in containment_rows:
        direct_contains[row.container_category_id].add(row.contained_category_id)

    return contains_map, dict(contained_by_map), direct_contains, dict(forward), containment_modes


def get_containment_edges():
    """Return all user-defined containment edges as dicts."""
    rows = CategoryContainment.query.all()
    result = []
    for r in rows:
        result.append({
            'id': r.id,
            'container_category_id': r.container_category_id,
            'container_category_name': r.container.name if r.container else None,
            'contained_category_id': r.contained_category_id,
            'contained_category_name': r.contained.name if r.contained else None,
            'mode': r.mode or 'subcategoria',
        })
    return result


def add_containment(container_id, contained_id, mode='subcategoria'):
    """Add a containment relationship. Raises ValueError on cycle or self-containment."""
    if container_id == contained_id:
        raise ValueError('Cannot contain itself')

    existing = (CategoryContainment.query
                .filter_by(container_category_id=container_id,
                           contained_category_id=contained_id)
                .first())
    if existing:
        existing.mode = mode
        db.session.commit()
        return existing

    # Check for cycles: if contained already contains container (transitively)
    contains_map, _, _, _, _ = build_containment_graph()
    if container_id in contains_map.get(contained_id, set()):
        raise ValueError('Adding this containment would create a cycle')

    edge = CategoryContainment(
        container_category_id=container_id,
        contained_category_id=contained_id,
        mode=mode,
    )
    db.session.add(edge)
    db.session.commit()
    return edge


def remove_containment(containment_id):
    """Remove a containment edge by id."""
    edge = CategoryContainment.query.get(containment_id)
    if not edge:
        return False
    db.session.delete(edge)
    db.session.commit()
    return True


def expand_category_ids(cat_ids, contains_map):
    """Expand a set of category IDs using the containment closure.

    Given a set of explicit category IDs, returns the full set including
    all categories that contain them (i.e. parents, grandparents, and
    user-defined containers).

    Args:
        cat_ids: iterable of category IDs
        contains_map: {cat_id: set of contained cat_ids} from build_containment_graph()

    Returns:
        set of category IDs (original + all containers)
    """
    result = set(cat_ids)
    for cid in cat_ids:
        # Find all categories that contain this one
        for container_id, contained_set in contains_map.items():
            if cid in contained_set:
                result.add(container_id)
    return result


def get_all_contained(cat_ids, contains_map):
    """Given explicit category IDs, return all categories they contain (transitively).

    Unlike expand_category_ids, this goes DOWN the hierarchy.
    """
    result = set()
    for cid in cat_ids:
        result.update(contains_map.get(cid, set()))
    return result
