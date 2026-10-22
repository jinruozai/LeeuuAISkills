/**
 * api.js — REST API client.
 */

const BASE = '';

async function request(method, path, body = null) {
    const opts = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };
    if (body !== null) {
        opts.body = JSON.stringify(body);
    }
    const res = await fetch(`${BASE}${path}`, opts);
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status}: ${text}`);
    }
    return res.json();
}

export const api = {
    getProject:       ()              => request('GET', '/api/project'),
    saveProject:      (data)          => request('PUT', '/api/project', data),
    listEntities:     (cat)           => request('GET', `/api/categories/${cat}/entities`),
    getEntity:        (cat, id)       => request('GET', `/api/categories/${cat}/entities/${id}`),
    saveEntity:       (cat, id, data) => request('PUT', `/api/categories/${cat}/entities/${id}`, { data }),
    createEntity:     (cat, data)     => request('POST', `/api/categories/${cat}/entities`, { data }),
    deleteEntity:     (cat, id)       => request('DELETE', `/api/categories/${cat}/entities/${id}`),
    genId:            ()              => request('GET', '/api/gen_id'),
};
