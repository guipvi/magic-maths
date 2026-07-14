"""
Category Analysis Engine (resource-pool model)

Replaces the linear-system approach with a resource-pool model where:
  - Assignments produce events in their category
  - Event limiters CONSUME from multiple source categories (AND/OR logic)
    and PRODUCE to a target category
  - Card triggers produce events in target category (with per-turn overrides)
  - accumulate on limiter: unconsumed source carries over between turns
  - max_per_turn on assignment: caps events contributed by that card per turn
  - containment: categories can contain others (parent-child + user-defined),
    propagating rollup, wait_for, limiters, accumulate
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


def _propagate_consumption(source_idx, consumed_amount, pool, cat_ids,
                           cat_index, contained_by_map, direct_children_of,
                           containment_modes=None):
    """Propagate consumption from a source category to all its containers.

    When events are consumed from a source, the corresponding diluted
    events in all containers should also be removed.

    Dilution factor per edge:
      - 'subcategoria': 1/n (n = number of direct children of the container)
      - 'ao_mesmo_tempo': 1/1 (full weight, no dilution)
      - hierarchy edges (no mode entry): 1/n (default)
    """
    if consumed_amount <= 0:
        return
    source_cat_id = cat_ids[source_idx]
    if source_cat_id not in contained_by_map:
        return
    for container_id in contained_by_map[source_cat_id]:
        if container_id in cat_index:
            cidx = cat_index[container_id]
            mode = (containment_modes or {}).get((container_id, source_cat_id))
            if mode == 'ao_mesmo_tempo':
                pool[cidx] = max(0.0, pool[cidx] - consumed_amount)
            else:
                n_ch = len(direct_children_of.get(container_id, set())) if direct_children_of else 1
                if n_ch > 0:
                    pool[cidx] = max(0.0, pool[cidx] - consumed_amount / n_ch)


def analyze_categories(deck_size, categories, assignments, max_turns=10,
                       card_triggers=None, limiters=None, containment_map=None,
                       direct_children_of=None, containment_modes=None):
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
    containment_map: dict {cat_id: set of cat_ids it contains} from build_containment_graph()
    direct_children_of: dict {cat_id: set of direct children} for 1/n dilution
    containment_modes: dict {(container_id, contained_id): mode} for user-defined edges

    Returns: dict with per-turn analysis

    Rollup uses two counters:
      - direct_count: 1:1 rollup (used for hypergeometric probability and summary)
      - effective_count/effective_weight: diluted rollup (used for pool calculation)
        When an event rolls up to a superior category:
          - subcategoria (or hierarchy): counts as 1/n where n = number of direct children
          - ao_mesmo_tempo: counts as 1/1 (full weight, card IS both things)
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

    # Build containment reverse map: {cat_id: set of category_ids that contain it}
    contained_by_map = {}  # cat_id -> set of cat_ids that contain it
    if containment_map:
        for cid, contained_set in containment_map.items():
            for inner_id in contained_set:
                contained_by_map.setdefault(inner_id, set()).add(cid)

    # Count cards per category
    direct_count = np.zeros(n_cats, dtype=int)   # 1:1 rollup (for hypergeom + summary)
    effective_count = np.zeros(n_cats)            # 1/n diluted rollup (for pool)
    direct_weight = np.zeros(n_cats)              # 1:1 rollup (for summary)
    effective_weight = np.zeros(n_cats)           # 1/n diluted rollup (for pool)
    max_per_turn_cat = {}  # category_id -> total max_per_turn from assignments
    max_per_turn_by_cat = np.zeros(n_cats)  # same in indexed form

    # Track wait_for info per assignment: index -> list of wait_for_category_ids
    wait_for_by_idx = {}  # cat_idx -> list of (wait_for_cat_indices)

    for assn in assignments:
        cid = assn['category_id']
        if cid in cat_index:
            idx = cat_index[cid]
            direct_count[idx] += 1
            effective_count[idx] += 1
            mult = assn.get('mana_amount') if assn.get('mana_amount') is not None else assn.get('multiplier', 1.0)
            direct_weight[idx] += mult
            effective_weight[idx] += mult
            mpt = assn.get('max_per_turn')
            if mpt is not None and mpt > 0:
                max_per_turn_by_cat[idx] += mpt
            # Roll up to parent categories (1:1 for direct_count, 1/n for effective)
            pid = cat_parent.get(cid)
            while pid is not None:
                if pid in cat_index:
                    pidx = cat_index[pid]
                    direct_count[pidx] += 1
                    direct_weight[pidx] += mult
                    n_children = len(direct_children_of.get(pid, set())) if direct_children_of else 0
                    if n_children > 0:
                        effective_count[pidx] += 1.0 / n_children
                        effective_weight[pidx] += mult / n_children
                    else:
                        effective_count[pidx] += 1
                        effective_weight[pidx] += mult
                    if mpt is not None and mpt > 0:
                        max_per_turn_by_cat[pidx] += mpt
                pid = cat_parent.get(pid)

            # Roll up through containment (mode-aware dilution)
            if cid in contained_by_map:
                for container_id in contained_by_map[cid]:
                    if container_id in cat_index and container_id != cid:
                        cidx = cat_index[container_id]
                        direct_count[cidx] += 1
                        direct_weight[cidx] += mult
                        mode = (containment_modes or {}).get((container_id, cid))
                        if mode == 'ao_mesmo_tempo':
                            effective_count[cidx] += 1
                            effective_weight[cidx] += mult
                        else:
                            n_children = len(direct_children_of.get(container_id, set())) if direct_children_of else 0
                            if n_children > 0:
                                effective_count[cidx] += 1.0 / n_children
                                effective_weight[cidx] += mult / n_children
                            else:
                                effective_count[cidx] += 1
                                effective_weight[cidx] += mult
                        if mpt is not None and mpt > 0:
                            max_per_turn_by_cat[cidx] += mpt

            # Store wait_for info (expanded via containment)
            wf_cats = assn.get('wait_for_category_ids')
            if wf_cats:
                wf_indices = set()
                for wc in wf_cats:
                    if wc in cat_index:
                        wf_indices.add(cat_index[wc])
                    # Also include all categories that contain this wait_for target
                    if wc in contained_by_map:
                        for container_id in contained_by_map[wc]:
                            if container_id in cat_index:
                                wf_indices.add(cat_index[container_id])
                if wf_indices:
                    wait_for_by_idx.setdefault(idx, []).append(list(wf_indices))

    # Per-card effective weight tracking (for limiter card filters)
    # cat_idx -> card_id -> effective_weight_in_this_category
    from collections import defaultdict
    card_eff_weight = defaultdict(lambda: defaultdict(float))

    for assn in assignments:
        cid = assn['category_id']
        if cid in cat_index:
            idx = cat_index[cid]
            card_id = assn['card_id']
            mult = assn.get('mana_amount') if assn.get('mana_amount') is not None else assn.get('multiplier', 1.0)
            card_eff_weight[idx][card_id] += mult
            # Roll up to parent categories
            pid = cat_parent.get(cid)
            while pid is not None:
                if pid in cat_index:
                    pidx = cat_index[pid]
                    n_ch = len(direct_children_of.get(pid, set())) if direct_children_of else 0
                    if n_ch > 0:
                        card_eff_weight[pidx][card_id] += mult / n_ch
                    else:
                        card_eff_weight[pidx][card_id] += mult
                pid = cat_parent.get(pid)
            # Roll up through containment
            if cid in contained_by_map:
                for container_id in contained_by_map[cid]:
                    if container_id in cat_index and container_id != cid:
                        cidx = cat_index[container_id]
                        mode = (containment_modes or {}).get((container_id, cid))
                        if mode == 'ao_mesmo_tempo':
                            card_eff_weight[cidx][card_id] += mult
                        else:
                            n_ch = len(direct_children_of.get(container_id, set())) if direct_children_of else 0
                            if n_ch > 0:
                                card_eff_weight[cidx][card_id] += mult / n_ch
                            else:
                                card_eff_weight[cidx][card_id] += mult

    # Identify draw category indices for iterative draw feedback
    draw_indices = set()
    for i, cid in enumerate(cat_ids):
        if cat_map[cid].get('config', {}).get('type') == 'draw':
            draw_indices.add(i)

    # 0. Convert assignment-level limiters to engine limiters
    if assignments:
        for assn in assignments:
            tgt_cat = assn.get('category_id')
            limit_cat = assn.get('limit_category_id')
            if limit_cat and tgt_cat:
                if limiters is None:
                    limiters = []
                # Check if this specific card-level limiter already exists as a deck limiter
                # (Simplified: just add it if not present)
                exists = any(l.get('target_category_id') == tgt_cat and 
                             limit_cat in l.get('source_category_ids', [])
                             for l in limiters)
                if not exists:
                    limiters.append({
                        'target_category_id': tgt_cat,
                        'logic': 'OR',
                        'source_category_ids': [limit_cat],
                        'trigger_count': 1,
                        'accumulate': False,
                        'source_card_filters': {limit_cat: [assn['card_id']]} if assn.get('limit_only_subsequent') else None
                    })

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

            # 2. Expected direct events (weighted by diluted effective weight)
            pool = np.zeros(n_cats)
            # Track which categories are targets of limiters to avoid double counting base events
            limiter_targets = set()
            if limiters:
                for lim in limiters:
                    limiter_targets.add(cat_index[lim['target_category_id']])

            for i in range(n_cats):
                # If a category is a target of a limiter, its events are produced by the limiter,
                # not by the base assignment (resource-pool model).
                if i in limiter_targets:
                    pool[i] = 0.0
                    continue

                raw = n_drawn * effective_weight[i] / deck_size if deck_size > 0 else 0.0
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
                    source_card_filters = lim.get('source_card_filters') or {}
                    # Expand source categories through containment
                    # Track (src_idx, original_cat_id) for card filter lookup
                    expanded_sources = []
                    for s in sources:
                        if s in cat_index:
                            expanded_sources.append((cat_index[s], s))
                            if containment_map and s in containment_map:
                                for contained_id in containment_map[s]:
                                    if contained_id in cat_index:
                                        expanded_sources.append((cat_index[contained_id], s))
                    if not expanded_sources:
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

                    def _src_available(src_idx, orig_cat_id):
                        card_filter = source_card_filters.get(orig_cat_id)
                        if not card_filter:
                            return pool[src_idx]
                        total_w = sum(card_eff_weight.get(src_idx, {}).values())
                        if total_w <= 0:
                            return 0.0
                        filtered_w = sum(card_eff_weight.get(src_idx, {}).get(cid, 0)
                                         for cid in card_filter)
                        return pool[src_idx] * (filtered_w / total_w)

                    if logic == 'OR':
                        total_available = sum(_src_available(si, oc)
                                              for si, oc in expanded_sources
                                              if pool[si] > 0)
                        if total_available <= 0:
                            continue
                        consumed_total = min(total_available, needed_events)
                        ratio = consumed_total / total_available
                        for si, oc in expanded_sources:
                            avail = _src_available(si, oc)
                            if avail > 0:
                                consumed_from_s = avail * ratio
                                consumed_from_s = min(consumed_from_s, pool[si])
                                pool[si] -= consumed_from_s
                                _propagate_consumption(si, consumed_from_s, pool, cat_ids,
                                                       cat_index, contained_by_map, direct_children_of,
                                                       containment_modes)
                        pool[tgt_idx] += consumed_total * count
                    elif logic == 'AND':
                        avail = [_src_available(si, oc) for si, oc in expanded_sources]
                        if any(a <= 0 for a in avail):
                            continue
                        per_source = min(avail)
                        consumed_total = min(per_source * len(avail), needed_events)
                        per_source_actual = consumed_total / len(avail)
                        for si, oc in expanded_sources:
                            pool[si] -= per_source_actual
                            _propagate_consumption(si, per_source_actual, pool, cat_ids,
                                                   cat_index, contained_by_map, direct_children_of,
                                                   containment_modes)
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
                            # Propagate surplus to containers
                            if src_id in contained_by_map:
                                for container_id in contained_by_map[src_id]:
                                    if container_id in cat_index:
                                        cidx = cat_index[container_id]
                                        surplus[cidx] = max(surplus[cidx], pool[s_idx])

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
                'expected': round(float(n_drawn * effective_weight[i] / deck_size if deck_size > 0 else 0.0), 2),
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
