/**
 * type_resolver.js — Resolve type override chain.
 * Walk up the `base` chain, merge properties. `params` is deep-merged.
 */

import { BASE_TYPES, isBaseType } from './builtins.js';

/**
 * Resolve a type key to its fully merged definition.
 * @param {string} typeKey - Type key or base type name
 * @param {object} types - The project's types dict from .gbdata
 * @returns {object} Merged type definition with: baseType, ui, params, default, label, template
 */
export function resolveType(typeKey, types = {}) {
    // Handle array[subtype] syntax
    let arraySubtype = null;
    const arrayMatch = typeKey.match(/^array\[(.+)\]$/);
    if (arrayMatch) {
        arraySubtype = arrayMatch[1];
        typeKey = 'array';
    }

    const chain = [];
    let current = typeKey;
    const visited = new Set();

    // Walk up the base chain
    while (current) {
        if (visited.has(current)) break; // Prevent cycles
        visited.add(current);

        if (isBaseType(current)) {
            chain.unshift({ ...BASE_TYPES[current], _key: current });
            break;
        }

        const typeDef = types[current];
        if (!typeDef) {
            // Unknown type, treat as string
            chain.unshift({ ...BASE_TYPES.string, _key: 'string' });
            break;
        }

        chain.unshift({ ...typeDef, _key: current });
        current = typeDef.base;
    }

    // Merge chain: first element is the root (base type)
    const result = {
        baseType: chain[0]?._key || 'string',
        ui: null,
        params: {},
        default: undefined,
        label: '',
        template: null,
    };

    for (const node of chain) {
        if (node.ui !== undefined) result.ui = node.ui;
        if (node.params) result.params = deepMerge(result.params, node.params);
        if (node.default !== undefined) result.default = node.default;
        if (node.label) result.label = node.label;
        if (node.template) result.template = node.template;
    }

    // Ensure ui has a value
    if (!result.ui) {
        result.ui = BASE_TYPES[result.baseType]?.ui || 'input';
    }

    // Ensure default has a value
    if (result.default === undefined) {
        result.default = BASE_TYPES[result.baseType]?.default ?? null;
    }

    if (arraySubtype) {
        result.arraySubtype = arraySubtype;
        result.baseType = 'array';
    }

    return result;
}

/**
 * Resolve a field definition to its full type + field overrides.
 */
export function resolveField(fieldKey, fields = {}, types = {}) {
    const fieldDef = fields[fieldKey];
    if (!fieldDef) return null;

    const resolved = resolveType(fieldDef.type || 'string', types);

    // Field-level overrides
    if (fieldDef.label) resolved.label = fieldDef.label;
    if (fieldDef.default !== undefined) resolved.default = fieldDef.default;
    if (fieldDef.card_slot) resolved.cardSlot = fieldDef.card_slot;
    if (fieldDef.required) resolved.required = true;
    if (fieldDef.description) resolved.description = fieldDef.description;

    resolved.fieldKey = fieldKey;
    return resolved;
}

/**
 * Get the effective default for a field in a category (category override → field default → type default).
 */
export function getFieldDefault(fieldKey, categoryFields = [], fields = {}, types = {}) {
    // Check category-level override
    for (const f of categoryFields) {
        if (typeof f === 'object' && f.key === fieldKey && f.default !== undefined) {
            return f.default;
        }
    }
    // Fall back to field/type chain
    const resolved = resolveField(fieldKey, fields, types);
    return resolved?.default ?? null;
}

function deepMerge(base, override) {
    const result = { ...base };
    for (const [key, val] of Object.entries(override)) {
        if (val && typeof val === 'object' && !Array.isArray(val) &&
            result[key] && typeof result[key] === 'object' && !Array.isArray(result[key])) {
            result[key] = deepMerge(result[key], val);
        } else {
            result[key] = val;
        }
    }
    return result;
}

/**
 * Get the root base type name for a type key.
 */
export function getRootBaseType(typeKey, types = {}) {
    const resolved = resolveType(typeKey, types);
    return resolved.baseType;
}
