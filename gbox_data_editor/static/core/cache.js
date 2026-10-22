/**
 * cache.js — Browser-side cache for unsaved changes (mirrors .gbdata.cache concept).
 * Uses localStorage to survive page refreshes and crashes.
 */

const CACHE_KEY = 'gbdata_editor_cache';

export const cache = {
    load() {
        try {
            const raw = localStorage.getItem(CACHE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    },

    save(data) {
        try {
            data.timestamp = new Date().toISOString();
            localStorage.setItem(CACHE_KEY, JSON.stringify(data));
        } catch (e) {
            console.error('Cache save failed:', e);
        }
    },

    clear() {
        localStorage.removeItem(CACHE_KEY);
    },

    hasPending() {
        const data = this.load();
        return data?.pending && Object.keys(data.pending).length > 0;
    }
};
