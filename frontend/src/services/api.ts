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
  goldfish: (data: { deck_id?: string; cards?: any[]; simulations?: number }) =>
    api.post('/analysis/goldfish', data),
  interactions: (data: { deck_id?: string; cards?: any[] }) =>
    api.post('/analysis/interactions', data),
  landRecommendation: (data: { deck_id?: string; cards?: any[] }) =>
    api.post('/analysis/land-recommendation', data),
  full: (data: { deck_id?: string; cards?: any[] }) =>
    api.post('/analysis/full', data),
};

export const scryfall = {
  search: (query: string) =>
    axios.get(`https://api.scryfall.com/cards/search?q=${encodeURIComponent(query)}&unique=prints`),
  getCard: (id: string) =>
    axios.get(`https://api.scryfall.com/cards/${id}`),
};

export default api;
