"""
Decklist Text Parser

Parses Magic: The Gathering decklists from plain text into a
structured format. Supports multiple input conventions:

- "1 Sol Ring" (quantity + name)
- "Sol Ring" (name only, defaults to qty 1)
- "// Name: My Deck" (deck name annotation)
- "Sideboard" or "SB:" separator for sideboard cards
- "(set)" and [collector_number] suffixes automatically stripped
- "Commander: Card Name" prefix for commander zone designation

Output: {name, mainboard: [{name, quantity, is_commander}],
         sideboard: [{name, quantity}], format}
"""

import re


def parse_decklist(text):
    lines = text.strip().split('\n')
    mainboard = []
    sideboard = []
    current_section = mainboard
    in_sideboard = False
    deck_name = ''

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        lower_line = line.lower()
        if lower_line.startswith('// name'):
            deck_name = line.split(':', 1)[1].strip() if ':' in line else ''
            continue

        if lower_line.startswith('sideboard') or lower_line.startswith('sb:'):
            in_sideboard = True
            current_section = sideboard
            continue

        if line.startswith('//') or line.startswith('#'):
            continue

        if in_sideboard and not re.match(r'^\d+\s*(?:x|X)?\b', line):
            if not re.match(r'^\d+\s*(?:x|X)?\s*$', line):
                continue

        parsed = _parse_line(line)
        if parsed:
            current_section.append(parsed)

    return {
        'name': deck_name,
        'mainboard': mainboard,
        'sideboard': sideboard,
        'format': _detect_format(mainboard),
    }


def _parse_line(line):
    line = line.strip()
    if not line:
        return None

    match = re.match(r'^(\d+)\s*(?:x|X)?\s*(.+)$', line)
    if match:
        quantity = int(match.group(1))
        name = match.group(2).strip()
    else:
        quantity = 1
        name = line.strip()

    if not name:
        return None

    name = re.sub(r'\s*\(.*?\)\s*$', '', name).strip()
    name = re.sub(r'\s*\[.*?\]\s*$', '', name).strip()

    is_commander = False
    if name.lower().startswith('commander:'):
        is_commander = True
        name = name[10:].strip()

    return {
        'name': name,
        'quantity': quantity,
        'is_commander': is_commander,
    }


def _detect_format(mainboard):
    total = sum(e['quantity'] for e in mainboard)
    if total == 100:
        return 'commander'
    if total == 60:
        return 'standard'
    if total <= 40:
        return 'limited'
    return 'custom'
