"""
Goldfish Speed Simulator

Simulates playing solitaire ("goldfishing") using category data to make
smart play decisions. Category-aware: ramp cards are prioritized to generate
extra mana, draw cards are cast to refill the hand.

No regex heuristics. Card behavior is known only through:
- Category assignments (ramp with mana_amount, draw, etc.)
- Card types (type_line) for land detection
- CMCs for casting decisions
"""

import numpy as np
from collections import defaultdict


def _is_land(card):
    tl = card.get('type_line', '')
    if not tl:
        return False
    tl_lower = tl.lower()
    if 'land' not in tl_lower:
        return False
    if '—' in tl:
        main_type = tl_lower.split('—')[0].strip()
        return 'land' in main_type
    return 'land' in tl_lower


def _build_category_map(assignments, categories):
    """Build card_id -> {type, mana_amount, name, category_id} from assignments."""
    cat_map = {}
    if not assignments or not categories:
        return cat_map

    cat_type = {c['id']: c.get('config', {}).get('type', '') for c in categories}
    cat_mana = {c['id']: c.get('config', {}).get('mana_amount') for c in categories}

    for a in assignments:
        cid = a.get('card_id')
        cat_id = a.get('category_id')
        ctype = cat_type.get(cat_id, '')
        if not ctype:
            continue
        if cid not in cat_map:
            cat_map[cid] = []
        mana_amt = a.get('mana_amount') or cat_mana.get(cat_id) or 0
        same_turn = a.get('same_turn')
        cat_map[cid].append({
            'type': ctype,
            'mana_amount': mana_amt,
            'same_turn': same_turn,
            'category_id': cat_id,
        })
    return cat_map


def _build_card_trigger_map(card_triggers):
    """Build lookup map for card triggers.

    Returns:
        card_trigger_map: {card_id: [(target_cat_id, trigger_count, per_turn)]}
    """
    card_trigger_map = defaultdict(list)

    if card_triggers:
        for ct in card_triggers:
            card_id = ct.get('source_card_id')
            tgt = ct.get('target_category_id')
            count = ct.get('trigger_count', 1)
            per_turn = ct.get('per_turn')
            if card_id and tgt:
                card_trigger_map[card_id].append((tgt, count, per_turn))

    return dict(card_trigger_map)


def _build_wait_for_map(assignments, categories, contained_by_map=None):
    """Build card_id -> set of wait_for_category_ids from assignments.

    If contained_by_map is provided, expand wait_for categories to include
    all categories that contain them (transitively).
    """
    wait_for_map = {}
    if not assignments:
        return wait_for_map
    for a in assignments:
        card_id = a.get('card_id')
        wf = a.get('wait_for_category_ids')
        if card_id and wf:
            expanded = set(wf)
            if contained_by_map:
                for wf_cat in wf:
                    if wf_cat in contained_by_map:
                        expanded.update(contained_by_map[wf_cat])
            wait_for_map[card_id] = expanded
    return wait_for_map


def _check_wait_for(card_id, battlefield, wait_for_map, card_to_categories):
    """Check if wait_for prerequisite is satisfied for a card.

    Returns True if the card has no wait_for or if any wait_for category
    has at least one card on the battlefield (OR logic).
    """
    wf_cats = wait_for_map.get(card_id)
    if not wf_cats:
        return True
    for bf_card_id in battlefield:
        bf_cats = card_to_categories.get(bf_card_id, set())
        if bf_cats & wf_cats:
            return True
    return False


def simulate_goldfish(deck_cards, deck_size=None, simulations=2000,
                       assignments=None, categories=None,
                       card_triggers=None, limiters=None,
                       containment_map=None, direct_children_of=None,
                       containment_modes=None):
    if deck_size is None:
        deck_size = sum(c.get('quantity', 1) for c in deck_cards)

    classified = []
    for c in deck_cards:
        qty = c.get('quantity', 1)
        classified.extend([c] * qty)

    total_cards = len(classified)
    land_count = sum(1 for c in classified if _is_land(c))
    nonland = [c for c in classified if not _is_land(c)]

    cat_map = _build_category_map(assignments, categories)
    card_trigger_map = _build_card_trigger_map(card_triggers)

    # Build contained_by_map for reverse containment lookup
    contained_by_map = {}
    if containment_map:
        for cid, contained_set in containment_map.items():
            for inner_id in contained_set:
                contained_by_map.setdefault(inner_id, set()).add(cid)

    wait_for_map = _build_wait_for_map(assignments, categories, contained_by_map)

    card_to_categories = defaultdict(set)
    if assignments:
        for a in assignments:
            card_to_categories[a.get('card_id')].add(a.get('category_id'))

    cat_type_by_id = {}
    if categories:
        for c in categories:
            cat_type_by_id[c['id']] = c.get('config', {}).get('type', '')

    cat_max_per_turn = defaultdict(float)
    if assignments:
        for a in assignments:
            cat_id = a.get('category_id')
            mpt = a.get('max_per_turn')
            if mpt is not None and mpt > 0:
                cat_max_per_turn[cat_id] += mpt

    # Build limiter lookup: {target_cat_id: [(source_cat_ids, logic, trigger_count, accumulate)]}
    limiter_map = defaultdict(list)
    if limiters:
        for lim in limiters:
            tgt = lim.get('target_category_id')
            src_ids = lim.get('source_category_ids', [])
            if tgt and src_ids:
                limiter_map[tgt].append({
                    'source_ids': src_ids,
                    'logic': lim.get('logic', 'OR'),
                    'trigger_count': lim.get('trigger_count', 1),
                    'accumulate': lim.get('accumulate', False),
                })

    rng = np.random.default_rng(42)
    results = defaultdict(list)

    for sim in range(simulations):
        deck = list(range(total_cards))
        rng.shuffle(deck)

        is_land_arr = [1 if _is_land(classified[i]) else 0 for i in range(total_cards)]
        cmc_arr = [int(classified[i].get('cmc', 0)) if not _is_land(classified[i]) else 0 for i in range(total_cards)]
        ramp_mana_arr = [0] * total_cards
        is_ramp_arr = [0] * total_cards
        is_draw_arr = [0] * total_cards
        same_turn_arr = [True] * total_cards

        for i, c in enumerate(classified):
            cid = c.get('id')
            if cid in cat_map:
                for entry in cat_map[cid]:
                    if entry['type'] == 'ramp':
                        is_ramp_arr[i] = 1
                        ramp_mana_arr[i] = int(entry.get('mana_amount', 0))
                        st = entry.get('same_turn')
                        if st is not None:
                            same_turn_arr[i] = st
                    elif entry['type'] == 'draw':
                        is_draw_arr[i] = 1

        hand_indices = deck[:7]
        library = deck[7:]
        hand = list(hand_indices)
        lands_played = 0
        extra_mana = 0
        cards_in_hand_by_turn = []
        max_mana_by_turn = []
        battlefield = set()

        for turn in range(1, 16):
            cast_this_turn_ids = set()
            if turn > 1 and library:
                drawn = library.pop(0)
                hand.append(drawn)

            hand_land_indices = [i for i in hand if is_land_arr[i]]
            if hand_land_indices:
                to_play = hand_land_indices[0]
                hand.remove(to_play)
                lands_played += 1

            mana_available = lands_played + extra_mana

            # Phase 1: play ramp cards (they generate extra mana)
            spent = True
            while spent:
                spent = False
                ramp_in_hand = [i for i in hand if is_ramp_arr[i] and not is_land_arr[i]
                                and cmc_arr[i] <= mana_available]
                if ramp_in_hand:
                    ramp_in_hand.sort(key=lambda i: cmc_arr[i])
                    to_cast = ramp_in_hand[0]
                    hand.remove(to_cast)
                    cast_this_turn_ids.add(classified[to_cast].get('id'))
                    mana_available -= cmc_arr[to_cast]
                    mana_gained = ramp_mana_arr[to_cast]
                    extra_mana += mana_gained
                    if same_turn_arr[to_cast]:
                        mana_available += mana_gained
                    spent = True

            # Phase 2: play draw cards if hand is low
            if len(hand) <= 3:
                spent = True
                while spent:
                    spent = False
                    draw_in_hand = [i for i in hand if is_draw_arr[i] and not is_land_arr[i]
                                    and cmc_arr[i] <= mana_available]
                    if draw_in_hand:
                        draw_in_hand.sort(key=lambda i: cmc_arr[i])
                        to_cast = draw_in_hand[0]
                        hand.remove(to_cast)
                        cast_this_turn_ids.add(classified[to_cast].get('id'))
                        mana_available -= cmc_arr[to_cast]
                        # Simulate drawing 1 card per draw spell
                        if library:
                            drawn = library.pop(0)
                            hand.append(drawn)
                        spent = True

            # Phase 3: play highest CMC affordable
            spent = True
            while spent and mana_available > 0 and hand:
                spent = False
                playable = [i for i in hand if not is_land_arr[i]
                            and cmc_arr[i] <= mana_available
                            and not is_ramp_arr[i]
                            and not is_draw_arr[i]]
                if playable:
                    playable.sort(key=lambda i: cmc_arr[i], reverse=True)
                    to_cast = playable[0]
                    hand.remove(to_cast)
                    cast_this_turn_ids.add(classified[to_cast].get('id'))
                    mana_available -= cmc_arr[to_cast]
                    spent = True

            # Phase 4: process triggers (e.g. sacrifice -> draw)
            # Add cast cards to battlefield first
            battlefield.update(cast_this_turn_ids)

            if cast_this_turn_ids and (card_trigger_map or limiter_map):
                trigger_draws = 0

                for card_id in cast_this_turn_ids:
                    if not _check_wait_for(card_id, battlefield, wait_for_map, card_to_categories):
                        continue
                    for tgt_cat_id, count, per_turn in card_trigger_map.get(card_id, []):
                        actual_count = count
                        if per_turn and isinstance(per_turn, list) and len(per_turn) >= turn:
                            actual_count = per_turn[turn - 1]
                            if actual_count == -1:
                                actual_count = count
                        if cat_type_by_id.get(tgt_cat_id) == 'draw':
                            trigger_draws += actual_count

                # Process event limiters (multi-source AND/OR)
                if limiter_map:
                    # Build source events from cast cards
                    source_events = defaultdict(float)
                    for card_id in cast_this_turn_ids:
                        for cat_id in card_to_categories.get(card_id, set()):
                            source_events[cat_id] += 1

                    limiter_draws = 0.0
                    for tgt_cat_id, limiter_list in limiter_map.items():
                        for lim in limiter_list:
                            src_ids = lim['source_ids']
                            logic = lim['logic']
                            count = lim['trigger_count']
                            cap = cat_max_per_turn.get(tgt_cat_id, 0)

                            if logic == 'OR':
                                total_available = sum(source_events.get(s, 0) for s in src_ids)
                                if total_available <= 0:
                                    continue
                                needed = float('inf')
                                if cap > 0:
                                    needed = max(0, cap) / count if count > 0 else 0
                                consumed = min(total_available, needed) if needed != float('inf') else total_available
                                ratio = consumed / total_available if total_available > 0 else 0
                                for s in src_ids:
                                    se = source_events.get(s, 0)
                                    if se > 0:
                                        consumed_from_s = se * ratio
                                        source_events[s] -= consumed_from_s
                                        # Propagate consumption to containers
                                        if s in contained_by_map:
                                            for container_id in contained_by_map[s]:
                                                mode = (containment_modes or {}).get((container_id, s))
                                                if mode == 'ao_mesmo_tempo':
                                                    source_events[container_id] = max(0, source_events.get(container_id, 0) - consumed_from_s)
                                                else:
                                                    n_ch = len(direct_children_of.get(container_id, set())) if direct_children_of else 1
                                                    if n_ch > 0:
                                                        source_events[container_id] = max(0, source_events.get(container_id, 0) - consumed_from_s / n_ch)
                                produced = consumed * count
                                if cat_type_by_id.get(tgt_cat_id) == 'draw':
                                    limiter_draws += produced

                            elif logic == 'AND':
                                avail = [source_events.get(s, 0) for s in src_ids]
                                if any(a <= 0 for a in avail):
                                    continue
                                per_source = min(avail)
                                needed = float('inf')
                                if cap > 0:
                                    needed = max(0, cap) / count if count > 0 else 0
                                consumed_total = min(per_source * len(src_ids), needed) if needed != float('inf') else per_source * len(src_ids)
                                per_source_actual = consumed_total / len(src_ids)
                                for s in src_ids:
                                    source_events[s] -= per_source_actual
                                    # Propagate consumption to containers
                                    if s in contained_by_map:
                                        for container_id in contained_by_map[s]:
                                            mode = (containment_modes or {}).get((container_id, s))
                                            if mode == 'ao_mesmo_tempo':
                                                source_events[container_id] = max(0, source_events.get(container_id, 0) - per_source_actual)
                                            else:
                                                n_ch = len(direct_children_of.get(container_id, set())) if direct_children_of else 1
                                                if n_ch > 0:
                                                    source_events[container_id] = max(0, source_events.get(container_id, 0) - per_source_actual / n_ch)
                                produced = consumed_total * count
                                if cat_type_by_id.get(tgt_cat_id) == 'draw':
                                    limiter_draws += produced

                    trigger_draws += limiter_draws

                for _ in range(int(trigger_draws)):
                    if library:
                        drawn = library.pop(0)
                        hand.append(drawn)

            cards_in_hand_by_turn.append(len(hand))
            max_mana_by_turn.append(lands_played + extra_mana)

            if not hand and not library:
                for t in range(turn, 16):
                    cards_in_hand_by_turn.append(0)
                    max_mana_by_turn.append(lands_played + extra_mana)
                break

            if not hand:
                turn_empty = turn
                for t_extra in range(1, 16 - turn):
                    if library:
                        drawn = library.pop(0)
                        hand.append(drawn)
                        if is_land_arr[drawn]:
                            lands_played += 1
                        if is_ramp_arr[drawn] and not is_land_arr[drawn]:
                            extra_mana += ramp_mana_arr[drawn]
                        mana_avail = lands_played + extra_mana
                        if is_ramp_arr[drawn] and not is_land_arr[drawn] and not same_turn_arr[drawn]:
                            mana_avail -= ramp_mana_arr[drawn]
                        hand_playable = [i for i in hand if not is_land_arr[i]
                                         and cmc_arr[i] <= mana_avail
                                         and not is_ramp_arr[i]
                                         and not is_draw_arr[i]]
                        if hand_playable:
                            hand_playable.sort(key=lambda i: cmc_arr[i], reverse=True)
                            to_cast = hand_playable[0]
                            hand.remove(to_cast)
                        cards_in_hand_by_turn.append(len(hand))
                        max_mana_by_turn.append(mana_avail)
                    else:
                        cards_in_hand_by_turn.append(len(hand))
                        max_mana_by_turn.append(lands_played + extra_mana)
                    if not hand and not library:
                        cards_in_hand_by_turn.append(0)
                        max_mana_by_turn.append(lands_played + extra_mana)
                break

        results['cards_in_hand'].append(cards_in_hand_by_turn[:16])
        results['max_mana'].append(max_mana_by_turn[:16])
        empty_turn = next((t + 1 for t, v in enumerate(cards_in_hand_by_turn) if v == 0), 16)
        results['empty_hand_turn'].append(empty_turn)

    max_turns = max(len(v) for v in results['cards_in_hand'])
    padded_hands = [v + [0] * (max_turns - len(v)) for v in results['cards_in_hand']]
    padded_mana = [v + [0] * (max_turns - len(v)) for v in results['max_mana']]

    arr_hands = np.array(padded_hands)
    arr_mana = np.array(padded_mana)
    arr_empty = np.array(results['empty_hand_turn'])

    summary = []
    for t in range(max_turns):
        hand_data = arr_hands[:, t]
        mana_data = arr_mana[:, t]
        summary.append({
            'turn': t + 1,
            'avg_cards_in_hand': round(float(np.mean(hand_data)), 2),
            'median_cards_in_hand': int(np.median(hand_data)),
            'p10_cards': int(np.percentile(hand_data, 10)),
            'p90_cards': int(np.percentile(hand_data, 90)),
            'avg_max_mana': round(float(np.mean(mana_data)), 2),
            'prob_empty_hand': round(float(np.mean(hand_data == 0)), 3),
        })

    return {
        'deck_size': total_cards,
        'land_count': land_count,
        'avg_empty_hand_turn': round(float(np.mean(arr_empty)), 1),
        'median_empty_hand_turn': int(np.median(arr_empty)),
        'p10_empty_turn': int(np.percentile(arr_empty, 10)),
        'p90_empty_turn': int(np.percentile(arr_empty, 90)),
        'probability_empty_by_turn_5': round(float(np.mean(arr_empty <= 5)), 3),
        'probability_empty_by_turn_7': round(float(np.mean(arr_empty <= 7)), 3),
        'turn_by_turn': summary,
        'deck_profile': {
            'land_count': land_count,
            'spell_count': total_cards - land_count,
            'avg_cmc': round(sum(c.get('cmc', 0) for c in nonland) / len(nonland), 2) if nonland else 0,
        },
    }
