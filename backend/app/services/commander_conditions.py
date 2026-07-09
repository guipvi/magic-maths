"""
Commander Conditions Evaluator

Handles evaluation of multiple conditions with AND/OR logic for commander casting.

Condition Group Structure:
{
    "id": "group_1",
    "operator": "AND" | "OR",  # How to combine conditions in this group
    "conditions": [
        {
            "id": "cond_1",
            "type": "category",  # Type of condition
            "category_id": 1,
            "required_count": 2,
            "operator": "AND" | "OR"  # How to combine with other conditions (for nested logic)
        },
        ...
    ]
}

Example:
- Group 1 (AND): [Category 1 >= 2, Category 2 >= 1]  -> All must be true
- Group 2 (OR): [Category 3 >= 1, Category 4 >= 1]   -> At least one must be true
- Final: Group 1 AND Group 2 -> Both groups must be satisfied
"""


def evaluate_condition(condition, category_analysis_by_turn, turn):
    """
    Evaluate a single condition at a given turn.
    
    Args:
        condition: dict with condition details
        category_analysis_by_turn: dict of turn -> {categories: {cat_id: {...}}}
        turn: turn number to evaluate
    
    Returns:
        bool: whether the condition is met
        float: probability of the condition being met
    """
    if condition['type'] != 'category':
        return False, 0.0
    
    category_id = condition.get('category_id')
    required_count = condition.get('required_count', 1)
    
    if not category_analysis_by_turn or turn not in category_analysis_by_turn:
        return False, 0.0
    
    cat_entry = category_analysis_by_turn[turn].get('categories', {}).get(category_id, {})
    pool_expected = cat_entry.get('total_expected', 0)
    
    # Get probability based on required count
    prob = 0.0
    if required_count == 1:
        prob = cat_entry.get('prob_at_least_1', 0.0)
    elif required_count == 2:
        prob = cat_entry.get('prob_at_least_2', 0.0)
    elif required_count == 3:
        prob = cat_entry.get('prob_at_least_3', 0.0)
    else:
        # For higher counts, use a conservative estimate
        prob = cat_entry.get('prob_at_least_1', 0.0) * (0.5 ** (required_count - 1))
    
    is_met = bool(pool_expected >= required_count)
    return is_met, prob


def evaluate_condition_group(group, category_analysis_by_turn, turn):
    """
    Evaluate a condition group (multiple conditions with AND/OR logic).
    
    Args:
        group: dict with operator and conditions list
        category_analysis_by_turn: dict of turn -> {categories: {...}}
        turn: turn number to evaluate
    
    Returns:
        bool: whether the group is satisfied
        float: probability of the group being satisfied
    """
    operator = group.get('operator', 'AND').upper()
    conditions = group.get('conditions', [])
    
    if not conditions:
        return True, 1.0
    
    results = []
    probabilities = []
    
    for condition in conditions:
        is_met, prob = evaluate_condition(condition, category_analysis_by_turn, turn)
        results.append(is_met)
        probabilities.append(prob)
    
    if operator == 'AND':
        # All conditions must be met
        group_met = all(results)
        # Conservative: use minimum probability
        group_prob = min(probabilities) if probabilities else 0.0
    elif operator == 'OR':
        # At least one condition must be met
        group_met = any(results)
        # Use maximum probability (optimistic for OR)
        group_prob = max(probabilities) if probabilities else 0.0
    else:
        group_met = False
        group_prob = 0.0
    
    return group_met, group_prob


def evaluate_all_condition_groups(condition_groups, category_analysis_by_turn, turn):
    """
    Evaluate all condition groups. Groups are combined with AND logic by default.
    
    Args:
        condition_groups: list of condition group dicts
        category_analysis_by_turn: dict of turn -> {categories: {...}}
        turn: turn number to evaluate
    
    Returns:
        dict with evaluation results
    """
    if not condition_groups:
        return {
            'all_met': True,
            'combined_probability': 1.0,
            'group_results': [],
        }
    
    group_results = []
    all_met = True
    probabilities = []
    
    for group in condition_groups:
        group_met, group_prob = evaluate_condition_group(group, category_analysis_by_turn, turn)
        group_results.append({
            'id': group.get('id'),
            'operator': group.get('operator', 'AND'),
            'is_met': group_met,
            'probability': round(group_prob, 4),
        })
        
        if not group_met:
            all_met = False
        
        probabilities.append(group_prob)
    
    # Combined probability: use minimum (conservative approach for AND between groups)
    combined_prob = min(probabilities) if probabilities else 0.0
    
    return {
        'all_met': all_met,
        'combined_probability': round(combined_prob, 4),
        'group_results': group_results,
    }


def get_condition_details_for_turn(condition_groups, category_analysis_by_turn, turn):
    """
    Get detailed breakdown of all conditions for a specific turn.
    
    Returns detailed information about each condition's status.
    """
    details = []
    
    for group in condition_groups:
        group_details = {
            'id': group.get('id'),
            'operator': group.get('operator', 'AND'),
            'conditions': [],
        }
        
        for condition in group.get('conditions', []):
            is_met, prob = evaluate_condition(condition, category_analysis_by_turn, turn)
            
            category_id = condition.get('category_id')
            cat_entry = {}
            if category_analysis_by_turn and turn in category_analysis_by_turn:
                cat_entry = category_analysis_by_turn[turn].get('categories', {}).get(category_id, {})
            
            group_details['conditions'].append({
                'id': condition.get('id'),
                'type': condition.get('type'),
                'category_id': category_id,
                'required_count': condition.get('required_count', 1),
                'expected_pool': round(cat_entry.get('total_expected', 0), 2),
                'probability': round(prob, 4),
                'is_met': is_met,
            })
        
        details.append(group_details)
    
    return details
