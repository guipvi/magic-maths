"""
Category Analysis Engine (resource-pool model)

Replaces the linear-system approach with a resource-pool model where:
  - Assignments produce events in their category
  - Category triggers CONSUME from source and PRODUCE to target (resource links)
  - Card triggers produce events in target category (with per-turn overrides)
  - accumulate on trigger: unconsumed source carries over between turns
  - max_per_turn on assignment: caps events contributed by that card per turn
"""

import numpy as np
from scipy.stats import hypergeom


def _hypergeom_pmf(N, K, n, k):
    if N <= 0 or K <= 0 or n <= 0 or k < 0:
        return 0.0
    if k > K or k > n:
        return 0.0
    try:
        return hypergeom.pmf(k, N, K, n)
    except Exception:
        return 0.0


def _hypergeom_cdf(N, K, n, k):
    if N <= 0 or K <= 0 or n <= 0:
        return 0.0
    try:
        return hypergeom.cdf(k, N, K, n)
    except Exception:
        return 0.0


def _bivariate_hypergeom_pmf(N, K1, K2, n, k1, k2):
    from scipy.special import comb
    if k1 < 0 or k2 < 0 or k1 + k2 > n:
        return 0.0
    if k1 > K1 or k2 > K2:
        return 0.0
    try:
        num = comb(K1, k1, exact=False) * comb(K2, k2, exact=False) * comb(N - K1 - K2, n - k1 - k2, exact=False)
        den = comb(N, n, exact=False)
        return num / den if den > 0 else 0.0
    except Exception:
        return 0.0


def analyze_categories(deck_size, categories, assignments, triggers, max_turns=10,
                       card_triggers=None):
    """
    categories: list of dicts [{'id', 'name', 'color', 'config'}]
    assignments: list of dicts [{'card_id', 'category_id', 'multiplier',
                                 'mana_amount', 'same_turn', 'is_permanent',
                                 'max_per_turn'}]
                 cards in the deck are already expanded by quantity
    triggers: list of dicts [{'source_category_id', 'target_category_id',
                              'trigger_count', 'accumulate'}]
    card_triggers: list of dicts [{'source_category_id', 'target_category_id',
                                   'trigger_count', 'quantity', 'per_turn'}]
    deck_size: total number of cards in deck

    Returns: dict with per-turn analysis
    """
    cat_ids = [c['id'] for c in categories]
    cat_map = {c['id']: c for c in categories}
    n_cats = len(cat_ids)
    cat_index = {cid: i for i, cid in enumerate(cat_ids)}

    # Count cards per category
    direct_count = np.zeros(n_cats, dtype=int)
    direct_weight = np.zeros(n_cats)  # sum of multipliers (unlimited)
    max_per_turn_cat = {}  # category_id -> total max_per_turn from assignments
    max_per_turn_by_cat = np.zeros(n_cats)  # same in indexed form
    
    # Track per-assignment max_per_turn
    assignment_caps = []  # list of (category_id, max_per_turn) per assignment copy

    for assn in assignments:
        cid = assn['category_id']
        if cid in cat_index:
            idx = cat_index[cid]
            direct_count[idx] += 1
            mult = assn.get('mana_amount') if assn.get('mana_amount') is not None else assn.get('multiplier', 1.0)
            direct_weight[idx] += mult
            mpt = assn.get('max_per_turn')
            if mpt is not None and mpt > 0:
                assignment_caps.append((cid, mpt))
                max_per_turn_by_cat[idx] += mpt

    # Build resource links: each category trigger is a flow from src to tgt
    # Processed in order, each unit of src consumed produces `count` units of tgt
    links = []  # (src_idx, tgt_idx, count, accumulate)
    for trig in triggers:
        src = trig['source_category_id']
        tgt = trig['target_category_id']
        count = trig.get('trigger_count', 1)
        accumulate = trig.get('accumulate', False)
        if src in cat_index and tgt in cat_index:
            links.append((cat_index[src], cat_index[tgt], count, accumulate))

    # Identify draw category indices for iterative draw feedback
    draw_indices = set()
    for i, cid in enumerate(cat_ids):
        if cat_map[cid].get('config', {}).get('type') == 'draw':
            draw_indices.add(i)

    # Surplus pool for accumulate categories
    surplus = np.zeros(n_cats)

    # Per-turn analysis
    by_turn = {}
    for turn in range(1, max_turns + 1):
        base_n_drawn = min(7 + (turn - 1), deck_size)
        n_drawn = base_n_drawn

        # Iterative feedback: draw spells increase effective cards drawn,
        # which increases probability of drawing more draw spells
        for _ in range(10):
            # 1. Expected direct cards drawn per category (hypergeometric mean)
            expected_direct_cards = np.array([
                n_drawn * direct_count[i] / deck_size if deck_size > 0 else 0.0
                for i in range(n_cats)
            ])

            # 2. Expected direct events (weighted by multiplier)
            pool = np.zeros(n_cats)
            for i in range(n_cats):
                if direct_count[i] > 0:
                    avg_mult = direct_weight[i] / direct_count[i]
                    raw = expected_direct_cards[i] * avg_mult
                    if max_per_turn_by_cat[i] > 0:
                        pool[i] = min(raw, max_per_turn_by_cat[i])
                    else:
                        pool[i] = raw

            # 2b. Card-trigger base events (per-card triggers with per_turn support)
            card_trigger_base = np.zeros(n_cats)
            if card_triggers:
                for ct in card_triggers:
                    src = ct.get('source_category_id')
                    tgt = ct.get('target_category_id')
                    qty = ct.get('quantity', 1)
                    per_turn = ct.get('per_turn')
                    if per_turn and isinstance(per_turn, list) and len(per_turn) >= turn:
                        count = per_turn[turn - 1]
                        if count == -1:
                            count = ct.get('trigger_count', 1)
                    else:
                        count = ct.get('trigger_count', 1)
                    if src in cat_index and tgt in cat_index:
                        tgt_idx = cat_index[tgt]
                        card_trigger_base[tgt_idx] += count * qty * n_drawn / deck_size

            pool += card_trigger_base

            # 3. Add surplus from previous turn (for accumulate categories)
            pool += surplus

            # 4. Pre-fuel: categories with max_per_turn need to consume fuel
            for tgt_idx in range(n_cats):
                if pool[tgt_idx] <= 0 or max_per_turn_by_cat[tgt_idx] <= 0:
                    continue
                events_to_fuel = pool[tgt_idx]
                for src_idx, tgt_idx2, count, accumulate in links:
                    if tgt_idx2 != tgt_idx or count <= 0:
                        continue
                    fuel_needed = events_to_fuel / count
                    fuel_used = min(pool[src_idx], fuel_needed)
                    events_fired = fuel_used * count
                    pool[src_idx] -= fuel_used
                    pool[tgt_idx] = events_fired
                    break

            # 5. Process resource links
            for src_idx, tgt_idx, count, accumulate in links:
                if pool[src_idx] <= 0:
                    continue
                target_headroom = float('inf')
                if max_per_turn_by_cat[tgt_idx] > 0:
                    target_headroom = max(0, max_per_turn_by_cat[tgt_idx] - pool[tgt_idx])
                max_source = target_headroom / count if count > 0 else 0
                consumed = min(pool[src_idx], max_source)
                pool[src_idx] -= consumed
                pool[tgt_idx] += consumed * count

            # Check convergence: extra draws from draw categories
            extra_draws = sum(pool[i] for i in draw_indices) if draw_indices else 0.0
            new_n_drawn = min(base_n_drawn + extra_draws, deck_size)

            if abs(new_n_drawn - n_drawn) < 0.1:
                n_drawn = new_n_drawn
                break
            n_drawn = new_n_drawn

        # 6. Compute surplus for next turn (only for accumulate categories)
        surplus.fill(0.0)
        for src_idx, tgt_idx, count, accumulate in links:
            if accumulate and pool[src_idx] > 0:
                surplus[src_idx] = pool[src_idx]

        # 7. Probability distribution for each category
        category_probs = {}
        for i, cid in enumerate(cat_ids):
            K = direct_count[i]
            if K == 0:
                category_probs[cid] = {
                    'expected': 0.0,
                    'total_expected': round(float(pool[i]), 2),
                    'prob_at_least_1': 0.0,
                    'prob_at_least_2': 0.0,
                    'prob_at_least_3': 0.0,
                    'pool': round(float(pool[i]), 2),
                    'card_triggered': round(float(card_trigger_base[i]), 2),
                }
                continue

            nd_int = int(n_drawn)
            probs = {}
            for thresh in [1, 2, 3]:
                prob = 1.0 - _hypergeom_cdf(deck_size, K, nd_int, thresh - 1)
                probs[f'prob_at_least_{thresh}'] = round(float(prob), 4)

            category_probs[cid] = {
                'expected': round(float(expected_direct_cards[i] * (direct_weight[i] / K if K > 0 else 0)), 2),
                'total_expected': round(float(pool[i]), 2),
                'pool': round(float(pool[i]), 2),
                'card_triggered': round(float(card_trigger_base[i]), 2),
                'max_per_turn': float(max_per_turn_by_cat[i]) if max_per_turn_by_cat[i] > 0 else None,
                **probs,
            }

        # 8. Joint probabilities for pairs
        joint_probs = {}
        for i in range(n_cats):
            for j in range(i + 1, n_cats):
                cid1, cid2 = cat_ids[i], cat_ids[j]
                K1, K2 = direct_count[i], direct_count[j]
                if K1 == 0 or K2 == 0:
                    continue
                key = f'{cid1}_{cid2}'
                joint_probs[key] = {}
                for t1 in [1, 2]:
                    for t2 in [1, 2]:
                        prob = 0.0
                        for k1 in range(t1, min(K1, int(n_drawn)) + 1):
                            max_k2 = min(K2, int(n_drawn) - k1)
                            for k2 in range(t2, max_k2 + 1):
                                prob += _bivariate_hypergeom_pmf(
                                    deck_size, K1, K2, int(n_drawn), k1, k2)
                        joint_probs[key][f'P(>={t1},{t2})'] = round(float(prob), 4)

        by_turn[turn] = {
            'turn': turn,
            'cards_drawn': round(float(n_drawn), 1),
            'categories': category_probs,
            'joint_probabilities': joint_probs,
        }

    # Summary statistics
    summary = []
    for c in categories:
        cid = c['id']
        idx = cat_index[cid]
        summary.append({
            'id': cid,
            'name': c['name'],
            'color': c.get('color', '#6366f1'),
            'cards_assigned': int(direct_count[idx]),
            'total_multiplier_sum': round(float(direct_weight[idx]), 1),
            'max_per_turn_total': float(max_per_turn_by_cat[idx]) if max_per_turn_by_cat[idx] > 0 else None,
        })

    return {
        'categories': summary,
        'by_turn': by_turn,
        'deck_size': deck_size,
    }
