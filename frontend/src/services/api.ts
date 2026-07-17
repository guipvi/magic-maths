/**
 * API Client — Axios wrapper para o backend Flask.
 *
 * Configurações:
 * - Base URL: /api (proxy Vite → localhost:5555 em dev)
 * - Interceptor de request: anexa Bearer token do localStorage
 * - Interceptor de response: redireciona para /login em 401
 *
 * Módulos exportados:
 * - auth:    register, login, me
 * - decks:   list, get, create, importDeck, update, delete
 * - collection: list, add, update, delete
 * - analysis: manaRamp, goldfish, interactions, landRecommendation, full, classifyCard
 * - scryfall: search, getCard (chamadas diretas à API pública)
 */
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const auth = {
  register: (data: { username: string; email: string; password: string }) =>
    api.post('/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
};

export const decks = {
  list: () => api.get('/decks'),
  get: (id: string) => api.get(`/decks/${id}`),
  create: (data: any) => api.post('/decks', data),
  importDeck: (data: { decklist: string; name?: string; format?: string }) =>
    api.post('/decks/import', data),
  update: (id: string, data: any) => api.put(`/decks/${id}`, data),
  delete: (id: string) => api.delete(`/decks/${id}`),
};

export const collection = {
  list: () => api.get('/collection'),
  add: (data: { card_name?: string; oracle_id?: string; quantity?: number; is_foil?: boolean; condition?: string }) =>
    api.post('/collection', data),
  update: (id: number, data: any) => api.put(`/collection/${id}`, data),
  delete: (id: number) => api.delete(`/collection/${id}`),
};

export const analysis = {
  manaRamp: (data: { deck_id?: string; cards?: any[] }) =>
    api.post('/analysis/mana-ramp', data),
  goldfish: (data: { deck_id?: string; cards?: any[]; simulations?: number; max_speed?: boolean }) =>
    api.post('/analysis/goldfish', data),
  interactions: (data: { deck_id?: string; cards?: any[] }) =>
    api.post('/analysis/interactions', data),
  landRecommendation: (data: { deck_id?: string; cards?: any[] }) =>
    api.post('/analysis/land-recommendation', data),
  full: (data: { deck_id?: string; cards?: any[]; max_speed?: boolean }) =>
    api.post('/analysis/full', data),
  whatIf: (data: { deck_id: string }) =>
    api.post('/analysis/what-if', data),
};

export const trades = {
  list: (deckId: string) => api.get(`/decks/${deckId}/trades`),
  create: (deckId: string, data: { card_out_name: string; card_in_name: string; quantity?: number }) =>
    api.post(`/decks/${deckId}/trades`, data),
  update: (deckId: string, tradeId: number, data: { planned_assignment?: any; planned_triggers?: any; quantity?: number }) =>
    api.put(`/decks/${deckId}/trades/${tradeId}`, data),
  remove: (deckId: string, tradeId: number) =>
    api.delete(`/decks/${deckId}/trades/${tradeId}`),
  execute: (deckId: string) =>
    api.post(`/decks/${deckId}/trades/execute`),
};

export const categories = {
  list: () => api.get('/categories'),
  tree: () => api.get('/categories/tree'),
  create: (data: { name: string; color?: string; config?: any; parent_id?: number | null }) =>
    api.post('/categories', data),
  update: (id: number, data: any) => api.put(`/categories/${id}`, data),
  delete: (id: number) => api.delete(`/categories/${id}`),
  getAssignments: (deckId: string) =>
    api.get(`/categories/deck/${deckId}/assignments`),
  setAssignment: (deckId: string, data: {
    card_id: number; category_id: number; multiplier?: number;
    mana_amount?: number | null; same_turn?: boolean | null;
    is_permanent?: boolean | null; max_per_turn?: number | null;
    tutored_card_id?: number | null; wait_for_category_ids?: number[];
    limit_category_id?: number | null; limit_only_subsequent?: boolean;
  }) => api.post(`/categories/deck/${deckId}/assignments`, data),
  removeAssignment: (deckId: string, assignmentId: number) =>
    api.delete(`/categories/deck/${deckId}/assignments/${assignmentId}`),
  getCardTriggers: (deckId: string) =>
    api.get(`/categories/deck/${deckId}/card-triggers`),
  setCardTrigger: (deckId: string, data: {
    source_category_id: number; source_card_id?: number | null;
    target_category_id: number;
    trigger_count?: number; per_turn?: (number | null)[] | null;
    is_permanent?: boolean | null; same_turn?: boolean | null;
  }) => api.post(`/categories/deck/${deckId}/card-triggers`, data),
  removeCardTrigger: (deckId: string, triggerId: number) =>
    api.delete(`/categories/deck/${deckId}/card-triggers/${triggerId}`),
  getLimiters: (deckId: string) =>
    api.get(`/categories/deck/${deckId}/limiters`),
  setLimiter: (deckId: string, data: {
    target_category_id: number; logic: 'AND' | 'OR';
    source_category_ids: number[]; trigger_count?: number; accumulate?: boolean;
    source_card_filters?: Record<number, number[] | null>;
  }) => api.post(`/categories/deck/${deckId}/limiters`, data),
  removeLimiter: (deckId: string, limiterId: number) =>
    api.delete(`/categories/deck/${deckId}/limiters/${limiterId}`),
  updateSourceFilter: (deckId: string, limiterId: number, sourceCategoryId: number, cardIdsFilter: number[] | null) =>
    api.put(`/categories/deck/${deckId}/limiters/${limiterId}/source-filter`, {
      source_category_id: sourceCategoryId,
      card_ids_filter: cardIdsFilter,
    }),
  getWaitFor: (deckId: string, assignmentId: number) =>
    api.get(`/categories/deck/${deckId}/assignments/${assignmentId}/wait-for`),
  setWaitFor: (deckId: string, assignmentId: number, categoryIds: number[]) =>
    api.post(`/categories/deck/${deckId}/assignments/${assignmentId}/wait-for`, { category_ids: categoryIds }),
  getContainment: () =>
    api.get('/categories/containment'),
  setContainment: (data: { container_category_id: number; contained_category_id: number; mode?: string }) =>
    api.post('/categories/containment', data),
  removeContainment: (containmentId: number) =>
    api.delete(`/categories/containment/${containmentId}`),
};

export const commander = {
  getConfig: (deckId: string) => api.get(`/decks/${deckId}/commander`),
  saveConfig: (deckId: string, data: {
    card_id: number;
    card_name?: string;
    mana_left_over?: number;
    min_category_requirements?: { category_id: number; count: number }[];
  }) => api.put(`/decks/${deckId}/commander`, data),
  deleteConfig: (deckId: string) => api.delete(`/decks/${deckId}/commander`),
};

export const scryfall = {
  search: (query: string) =>
    axios.get(`https://api.scryfall.com/cards/search?q=${encodeURIComponent(query)}&unique=prints`),
  getCard: (id: string) =>
    axios.get(`https://api.scryfall.com/cards/${id}`),
};

export default api;
