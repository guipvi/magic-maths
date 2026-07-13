"""
Category Analysis Engine (resource-pool model)

Replaces the linear-system approach with a resource-pool model where:
  - Assignments produce events in their category
  - Event limiters CONSUME from multiple source categories (AND/OR logic)
    and PRODUCE to a target category
  - Card triggers produce events in target category (with per-turn overrides)
  - accumulate on limiter: unconsumed source carries over between turns
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


def analyze_categories(deck_size, categories, assignments, max_turns=10,
                       card_triggers=None, limiters=None):
    """
    categories: list of dicts [{'id', 'name', 'color', 'config'}]
    assignments: list of dicts [{'card_id', 'category_id', 'multiplier',
                                 'mana_amount', 'same_turn', 'is_permanent',
                                 'max_per_turn', 'wait_for_category_ids'}]
                 cards in the deck are already expanded by quantity
    card_triggers: list of dicts [{'source_category_id', 'target_category_id',
                                   'trigger_count', 'quantity', 'per_turn'}]
    limiters: list of dicts [{'target_category_id', 'logic', 'source_category_ids',
                              'trigger_count', 'accumulate'}]
    deck_size: total number of cards in deck

    Returns: dict with per-turn analysis
    """
    cat_ids = [c['id'] for c in categories]
    cat_map = {c['id']: c for c in categories}
    n_cats = len(cat_ids)
    cat_index = {cid: i for i, cid in enumerate(cat_ids)}

    # Build parent<->child mapping for hierarchy rollup
    cat_parent = {c['id']: c.get('parent_id') for c in categories}
    child_ids_of = {}
    for c in categories:
        pid = c.get('parent_id')
        if pid is not None:
            child_ids_of.setdefault(pid, []).append(c['id'])

    # Count cards per category
    direct_count = np.zeros(n_cats, dtype=int)
    direct_weight = np.zeros(n_cats)  # sum of multipliers (unlimited)
    max_per_turn_cat = {}  # category_id -> total max_per_turn from assignments
    max_per_turn_by_cat = np.zeros(n_cats)  # same in indexed form
    
    # Track per-assignment max_per_turn
    assignment_caps = []  # list of (category_id, max_per_turn) per assignment copy

    # Track wait_for info per assignment: index -> list of wait_for_category_ids
    wait_for_by_idx = {}  # cat_idx -> list of (wait_for_cat_indices)

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
            # Roll up to parent categories
            pid = cat_parent.get(cid)
            while pid is not None:
                if pid in cat_index:
                    pidx = cat_index[pid]
                    direct_count[pidx] += 1
                    direct_weight[pidx] += mult
                    if mpt is not None and mpt > 0:
                        max_per_turn_by_cat[pidx] += mpt
                pid = cat_parent.get(pid)

            # Store wait_for info
            wf_cats = assn.get('wait_for_category_ids')
            if wf_cats:
                wf_indices = [cat_index[wc] for wc in wf_cats if wc in cat_index]
                if wf_indices:
                    wait_for_by_idx.setdefault(idx, []).append(wf_indices)

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

            # 2a. Wait-for probability gate: multiply pool by P(wait_for satisfied)
            nd_int = int(n_drawn)
            for i in range(n_cats):
                if i not in wait_for_by_idx or pool[i] <= 0:
                    continue
                for wf_indices in wait_for_by_idx[i]:
                    # OR logic: P(at least 1) = 1 - product(P(0 from each))
                    p_none_product = 1.0
                    for wf_idx in wf_indices:
                        K_wf = direct_count[wf_idx]
                        p_zero = _hypergeom_cdf(deck_size, K_wf, nd_int, 0)
                        p_none_product *= p_zero
                    p_gate = 1.0 - p_none_product
                    pool[i] *= p_gate

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

            # 4. Process event limiters (multi-source AND/OR)
            if limiters:
                for lim in limiters:
                    tgt = lim.get('target_category_id')
                    if tgt not in cat_index:
                        continue
                    tgt_idx = cat_index[tgt]
                    sources = lim.get('source_category_ids', [])
                    src_indices = [cat_index[s] for s in sources if s in cat_index]
                    if not src_indices:
                        continue
                    count = lim.get('trigger_count', 1)
                    logic = lim.get('logic', 'OR')

                    # Compute headroom for target
                    target_headroom = float('inf')
                    if max_per_turn_by_cat[tgt_idx] > 0:
                        target_headroom = max(0, max_per_turn_by_cat[tgt_idx] - pool[tgt_idx])
                    if target_headroom <= 0:
                        continue
                    needed_events = target_headroom / count if count > 0 else 0

                    if logic == 'OR':
                        total_available = sum(pool[s] for s in src_indices if pool[s] > 0)
                        if total_available <= 0:
                            continue
                        consumed_total = min(total_available, needed_events)
                        ratio = consumed_total / total_available
                        for s in src_indices:
                            if pool[s] > 0:
                                pool[s] *= (1.0 - ratio)
                        pool[tgt_idx] += consumed_total * count
                    elif logic == 'AND':
                        avail = [pool[s] for s in src_indices if pool[s] > 0]
                        if len(avail) < len(src_indices):
                            continue
                        per_source = min(avail)
                        consumed_total = min(per_source * len(src_indices), needed_events)
                        per_source_actual = consumed_total / len(src_indices)
                        for s in src_indices:
                            pool[s] -= per_source_actual
                        pool[tgt_idx] += consumed_total * count

            # Check convergence: extra draws from draw categories
            extra_draws = sum(pool[i] for i in draw_indices) if draw_indices else 0.0
            new_n_drawn = min(base_n_drawn + extra_draws, deck_size)

            if abs(new_n_drawn - n_drawn) < 0.1:
                n_drawn = new_n_drawn
                break
            n_drawn = new_n_drawn

        # 5. Compute surplus for next turn (only for accumulate limiters)
        surplus.fill(0.0)
        if limiters:
            for lim in limiters:
                if not lim.get('accumulate', False):
                    continue
                for src_id in lim.get('source_category_ids', []):
                    if src_id in cat_index:
                        s_idx = cat_index[src_id]
                        if pool[s_idx] > 0:
                            surplus[s_idx] = pool[s_idx]

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
            'parent_id': c.get('parent_id'),
            'cards_assigned': int(direct_count[idx]),
            'total_multiplier_sum': round(float(direct_weight[idx]), 1),
            'max_per_turn_total': float(max_per_turn_by_cat[idx]) if max_per_turn_by_cat[idx] > 0 else None,
        })

    return {
        'categories': summary,
        'by_turn': by_turn,
        'deck_size': deck_size,
    }
