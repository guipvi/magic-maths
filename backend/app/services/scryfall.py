"""
Scryfall API Integration Service

Provides a caching layer on top of the Scryfall REST API
(https://api.scryfall.com). Cards fetched from the API are stored
in the local SQLite database to avoid redundant network calls.

Lookup order (fetch_or_get_card):
1. Local DB by oracle_id (exact match)
2. Local DB by card name (case-insensitive)
3. Scryfall /cards/named?exact=<name> (exact name search)
4. Scryfall /cards/search?q=<name> (fallback fuzzy search)

Requires a custom User-Agent header per Scryfall API policy.
"""

import requests
import logging
from app.extensions import db
from app.models.card import Card

logger = logging.getLogger(__name__)
SCRYFALL_API = 'https://api.scryfall.com'


HEADERS = {
    'User-Agent': 'MagicMaths/1.0 (https://github.com/magicmaths; guilherme@example.com)',
    'Accept': 'application/json',
}


def _scryfall_request(endpoint, params=None):
    url = f'{SCRYFALL_API}{endpoint}'
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        if resp.status_code == 404:
            return None
        logger.warning(f'Scryfall HTTP {resp.status_code}: {url} - {resp.text[:200]}')
        return None
    except requests.RequestException as e:
        logger.warning(f'Scryfall request failed: {url} - {e}')
        return None


def _card_from_scryfall(data):
    if not data:
        return None
    if data.get('object') == 'card':
        card_data = data
    elif data.get('object') == 'list' and data.get('data'):
        card_data = data['data'][0]
    else:
        return None

    img_uris = card_data.get('image_uris', {})
    if not img_uris and 'card_faces' in card_data:
        img_uris = card_data['card_faces'][0].get('image_uris', {})

    prices = card_data.get('prices', {})

    card = Card(
        oracle_id=card_data['oracle_id'],
        scryfall_id=card_data['id'],
        name=card_data['name'],
        cmc=card_data.get('cmc', 0),
        mana_cost=card_data.get('mana_cost', ''),
        colors=card_data.get('colors', []),
        color_identity=card_data.get('color_identity', []),
        type_line=card_data.get('type_line', ''),
        oracle_text=card_data.get('oracle_text', ''),
        power=card_data.get('power', ''),
        toughness=card_data.get('toughness', ''),
        rarity=card_data.get('rarity', ''),
        set_name=card_data.get('set_name', ''),
        set_code=card_data.get('set', ''),
        prices=prices,
        image_uris=img_uris,
    )
    return card


def fetch_or_get_card(name_or_id):
    if not name_or_id:
        return None

    card = Card.query.filter_by(oracle_id=name_or_id).first()
    if card:
        return card

    card = Card.query.filter(
        Card.name.ilike(name_or_id.strip())
    ).first()
    if card:
        return card

    if len(name_or_id) == 36 and '-' in name_or_id:
        data = _scryfall_request(f'/cards/{name_or_id}')
    else:
        data = _scryfall_request('/cards/named', {'exact': name_or_id.strip()})
        if not data:
            data = _scryfall_request('/cards/search', {'q': name_or_id.strip(), 'unique': 'prints'})
            if data and data.get('data'):
                data = data['data'][0]

    if not data:
        return None

    card = _card_from_scryfall(data)
    if card:
        db.session.add(card)
        db.session.commit()
    return card


def search_cards(query, page=1):
    params = {
        'q': query,
        'page': page,
        'unique': 'prints',
    }
    data = _scryfall_request('/cards/search', params)
    if not data or not data.get('data'):
        return {'cards': [], 'total': 0, 'has_more': False}
    return {
        'cards': data['data'],
        'total': data.get('total_cards', 0),
        'has_more': data.get('has_more', False),
    }
