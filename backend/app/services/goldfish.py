"""
Goldfish Speed Simulator (Feature 2)

Simulates playing solitaire ("goldfishing") at maximum speed to determine
how quickly the hand empties.

Algorithm per simulation:
1. Shuffle deck, draw opening 7
2. Each turn: play a land if available, then play the highest-CMC
   spell that fits in available mana
3. Repeat until turn 15 or until deck is exhausted
4. Track cards-in-hand and mana-available per turn across 2000 sims

Output: average/median/P10/P90 turn when hand is empty, plus
probability of empty hand by turns 5 and 7.
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


def _cmc_buckets(cards):
    buckets = defaultdict(list)
    for c in cards:
        if _is_land(c):
            continue
        cmc = int(c.get('cmc', 0))
        if cmc > 12:
            cmc = 12
        buckets[cmc].append(c)
    return buckets


def simulate_goldfish(deck_cards, deck_size=None, simulations=2000):
    if deck_size is None:
        deck_size = sum(c.get('quantity', 1) for c in deck_cards)

    classified = []
    for c in deck_cards:
        qty = c.get('quantity', 1)
        classified.extend([c] * qty)

    land_count = sum(1 for c in classified if _is_land(c))
    nonland = [c for c in classified if not _is_land(c)]
    cmc_buckets = _cmc_buckets(nonland)
    total_cards = len(classified)

    rng = np.random.default_rng(42)
    results = defaultdict(list)

    for sim in range(simulations):
        deck = list(range(total_cards))
        rng.shuffle(deck)

        is_land_arr = [1 if _is_land(classified[i]) else 0 for i in range(total_cards)]
        cmc_arr = [int(classified[i].get('cmc', 0)) if not _is_land(classified[i]) else 0 for i in range(total_cards)]

        hand_indices = deck[:7]
        library = deck[7:]
        hand = list(hand_indices)
        lands_played = 0
        cards_in_hand_by_turn = []
        max_mana_by_turn = []

        for turn in range(1, 16):
            if turn > 1 and library:
                drawn = library.pop(0)
                hand.append(drawn)

            hand_land_indices = [i for i in hand if is_land_arr[i]]

            if hand_land_indices:
                to_play = hand_land_indices[0]
                hand.remove(to_play)
                lands_played += 1

            mana_available = lands_played

            spent = True
            while spent and mana_available > 0 and hand:
                spent = False
                playable = [i for i in hand if not is_land_arr[i] and cmc_arr[i] <= mana_available]
                if playable:
                    playable.sort(key=lambda i: cmc_arr[i], reverse=True)
                    to_cast = playable[0]
                    hand.remove(to_cast)
                    mana_available -= cmc_arr[to_cast]
                    spent = True

            cards_in_hand_by_turn.append(len(hand))
            max_mana_by_turn.append(lands_played)

            if not hand and not library:
                for t in range(turn, 16):
                    cards_in_hand_by_turn.append(0)
                    max_mana_by_turn.append(lands_played)
                break

            if not hand:
                turn_empty = turn
                for t_extra in range(1, 16 - turn):
                    if library:
                        drawn = library.pop(0)
                        hand.append(drawn)
                        if is_land_arr[drawn]:
                            lands_played += 1
                        hand_playable = [i for i in hand if not is_land_arr[i] and cmc_arr[i] <= lands_played]
                        if hand_playable:
                            hand_playable.sort(key=lambda i: cmc_arr[i], reverse=True)
                            to_cast = hand_playable[0]
                            hand.remove(to_cast)
                        cards_in_hand_by_turn.append(len(hand))
                        max_mana_by_turn.append(lands_played)
                    else:
                        cards_in_hand_by_turn.append(len(hand))
                        max_mana_by_turn.append(lands_played)
                    if not hand and not library:
                        cards_in_hand_by_turn.append(0)
                        max_mana_by_turn.append(lands_played)
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
