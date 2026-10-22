/**
 * validator.js — Field value validation.
 */

import { resolveField, getRootBaseType } from './type_resolver.js';

/**
 * Validate a single field value.
 * @returns {string|null} Error message or null if valid.
 */
export function validateField(fieldKey, value, fields, types) {
    const resolved = resolveField(fieldKey, fields, types);
    if (!resolved) return `Unknown field: ${fieldKey}`;

    // Required check
    if (resolved.required && (value === null || value === undefined || value === '')) {
        return `${resolved.label || fieldKey} is required`;
    }

    // Skip further checks if value is empty and not required
    if (value === null || value === undefined) return null;

    // Base type check
    const baseType = resolved.baseType || getRootBaseType(resolved.type, types);
    switch (baseType) {
        case 'int':
            if (typeof value !== 'number' || !Number.isInteger(value)) {
                return `${resolved.label} must be an integer`;
            }
            if (resolved.params.min !== undefined && value < resolved.params.min) {
                return `${resolved.label} must be >= ${resolved.params.min}`;
            }
            if (resolved.params.max !== undefined && value > resolved.params.max) {
                return `${resolved.label} must be <= ${resolved.params.max}`;
            }
            break;
        case 'float':
            if (typeof value !== 'number') {
                return `${resolved.label} must be a number`;
            }
            if (resolved.params.min !== undefined && value < resolved.params.min) {
                return `${resolved.label} must be >= ${resolved.params.min}`;
            }
            if (resolved.params.max !== undefined && value > resolved.params.max) {
                return `${resolved.label} must be <= ${resolved.params.max}`;
            }
            break;
        case 'string':
            if (typeof value !== 'string') {
                return `${resolved.label} must be a string`;
            }
            break;
        case 'array':
            if (!Array.isArray(value)) {
                return `${resolved.label} must be an array`;
            }
            break;
    }

    return null;
}

/**
 * Validate all fields of an entity.
 * @returns {object} Map of fieldKey → error message (only fields with errors).
 */
export function validateEntity(entity, categoryFields, fields, types) {
    const errors = {};
    for (const f of categoryFields) {
        const fkey = typeof f === 'string' ? f : f.key;
        const err = validateField(fkey, entity[fkey], fields, types);
        if (err) errors[fkey] = err;
    }
    return errors;
}
