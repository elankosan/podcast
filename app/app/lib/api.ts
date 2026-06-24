const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export interface Podcast {
  id: string;
  title: string;
  description: string;
  language: string;
  target_languages: string[];
  owner_id: string;
}

export interface Episode {
  id: string;
  podcast_id: string;
  title: string;
  vision: string;
  status: string;
  created_at: string;
}

export interface Version {
  id: string;
  episode_id: string;
  version_number: number;
  version_type: string;
  content: any;
  metadata?: any;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

async function apiFetch(path: string, options: RequestInit = {}) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  auth: {
    login: (email: string, password: string) =>
      apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }),
    me: () => apiFetch('/api/auth/me'),
  },
  podcasts: {
    list: () => apiFetch('/api/podcasts') as Promise<Podcast[]>,
    get: (id: string) => apiFetch(`/api/podcasts/${id}`) as Promise<Podcast>,
    create: (data: Partial<Podcast>) =>
      apiFetch('/api/podcasts', { method: 'POST', body: JSON.stringify(data) }),
    episodes: (id: string) => apiFetch(`/api/podcasts/${id}/episodes`) as Promise<Episode[]>,
  },
  episodes: {
    get: (id: string) => apiFetch(`/api/episodes/${id}`) as Promise<Episode>,
    create: (podcastId: string, data: Partial<Episode>) =>
      apiFetch(`/api/podcasts/${podcastId}/episodes`, { method: 'POST', body: JSON.stringify(data) }),
    research: (id: string) => apiFetch(`/api/research/${id}/research`, { method: 'POST' }),
    getResearch: (id: string) => apiFetch(`/api/research/${id}/research`),
    script: (id: string) => apiFetch(`/api/scripts/${id}/script`, { method: 'POST' }),
    getScript: (id: string) => apiFetch(`/api/scripts/${id}/script`),
    translate: (id: string, language: string) =>
      apiFetch(`/api/translations/${id}/translate?language=${language}`, { method: 'POST' }),
    getTranslations: (id: string) => apiFetch(`/api/translations/${id}/translations`) as Promise<{ translations: Version[] }>,
  },
};
