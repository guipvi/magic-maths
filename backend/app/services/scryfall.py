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

Rate limiting:
- Enforces a 100ms minimum interval between requests (max 10 req/s).
- Retries on 429 with respect for the Retry-After header.
- Uses an in-memory response cache to avoid redundant API calls.

Requires a custom User-Agent header per Scryfall API policy.
"""

import time
import requests
import logging
from threading import Lock
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from app.extensions import db
from app.models.card import Card

logger = logging.getLogger(__name__)
SCRYFALL_API = 'https://api.scryfall.com'

HEADERS = {
    'User-Agent': 'MagicMaths/1.0 (https://github.com/magicmaths; guilherme@example.com)',
    'Accept': 'application/json',
}

MIN_REQUEST_INTERVAL = 0.1
_last_request_time = 0.0
_rate_limit_lock = Lock()
_response_cache = {}
_fetch_cache = {}

_session = None


def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(HEADERS)
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET'],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        _session.mount('https://', adapter)
        _session.mount('http://', adapter)
    return _session


def _scryfall_request(endpoint, params=None, max_retries=3):
    url = f'{SCRYFALL_API}{endpoint}'

    cache_key = (endpoint, tuple(sorted((params or {}).items())))
    if cache_key in _response_cache:
        return _response_cache[cache_key]

    session = _get_session()

    for attempt in range(max_retries):
        with _rate_limit_lock:
            global _last_request_time
            elapsed = time.time() - _last_request_time
            if elapsed < MIN_REQUEST_INTERVAL:
                time.sleep(MIN_REQUEST_INTERVAL - elapsed)
            _last_request_time = time.time()

        resp = None
        try:
            resp = session.get(url, params=params, timeout=(5, 10))
        except Exception as e:
            logger.warning(f'Scryfall request failed (attempt {attempt + 1}/{max_retries}): {url} - {e}')
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None

        if resp is None:
            return None

        if resp.status_code == 429:
            retry_after = resp.headers.get('retry-after', '?')
            logger.warning(
                f'Scryfall rate limited (attempt {attempt + 1}/{max_retries}). '
                f'Retry-After: {retry_after}s — skipping card to avoid worker timeout'
            )
            return None

        if resp.status_code == 404:
            return None

        if resp.status_code >= 500:
            logger.warning(
                f'Scryfall server error {resp.status_code}: {url} (attempt {attempt + 1}/{max_retries})'
            )
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None

        try:
            resp.raise_for_status()
            result = resp.json()
            _response_cache[cache_key] = result
            return result
        except requests.HTTPError:
            logger.warning(f'Scryfall HTTP {resp.status_code}: {url} - {resp.text[:200]}')
            return None

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

    cache_key = name_or_id.strip().lower()
    if cache_key in _fetch_cache:
        return _fetch_cache[cache_key]

    card = Card.query.filter_by(oracle_id=name_or_id).first()
    if card:
        _fetch_cache[cache_key] = card
        return card

    card = Card.query.filter(
        Card.name.ilike(name_or_id.strip())
    ).first()
    if card:
        _fetch_cache[cache_key] = card
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
        _fetch_cache[cache_key] = card
    return card


def _scryfall_post(endpoint, json_body):
    url = f'{SCRYFALL_API}{endpoint}'
    session = _get_session()

    with _rate_limit_lock:
        global _last_request_time
        elapsed = time.time() - _last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        _last_request_time = time.time()

    try:
        resp = session.post(url, json=json_body, timeout=(5, 30))
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f'Scryfall POST failed: {url} - {e}')
        return None


def fetch_or_get_cards_bulk(names):
    if not names:
        return {}

    results = {}
    uncached = []

    for name in names:
        if not name:
            continue
        cache_key = name.strip().lower()
        if cache_key in _fetch_cache:
            results[name] = _fetch_cache[cache_key]
            continue

        card = Card.query.filter(Card.name.ilike(name.strip())).first()
        if card:
            _fetch_cache[cache_key] = card
            _fetch_cache[card.oracle_id] = card
            results[name] = card
        else:
            uncached.append(name.strip())

    if not uncached:
        return results

    for i in range(0, len(uncached), 75):
        batch = uncached[i:i+75]
        data = _scryfall_post('/cards/collection', {
            "identifiers": [{"name": n} for n in batch]
        })
        if data and data.get('data'):
            for card_data in data['data']:
                card = _card_from_scryfall(card_data)
                if card:
                    db.session.add(card)
                    _fetch_cache[card.name.lower()] = card
                    _fetch_cache[card.oracle_id] = card

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()

    for name in uncached:
        lower = name.lower()
        card = _fetch_cache.get(lower)
        if card:
            results[name] = card
        else:
            card = fetch_or_get_card(name)
            if card:
                results[name] = card

    return results


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
