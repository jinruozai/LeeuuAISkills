/**
 * builtins.js — All built-in definitions in one place.
 * Base types, UI component declarations, card slots, defaults.
 */

// ── Base types (roots of the override chain) ──

export const BASE_TYPES = {
    int:    { label: 'Integer',  ui: 'input', default: 0,    rawType: 'int' },
    float:  { label: 'Float',    ui: 'input', default: 0.0,  rawType: 'float' },
    string: { label: 'String',   ui: 'input', default: '',   rawType: 'string' },
    array:  { label: 'Array',    ui: 'list',  default: [],   rawType: 'array' },
};

export const BASE_TYPE_NAMES = Object.keys(BASE_TYPES);

// ── UI component declarations ──
// Each declares which base types it can bind to, and its default params.

export const UI_COMPONENTS = {
    input:      { label: 'Text Input',       baseTypes: ['int', 'float', 'string'], defaultParams: {} },
    textarea:   { label: 'Text Area',        baseTypes: ['string'],                 defaultParams: { rows: 3 } },
    range:      { label: 'Range Slider',     baseTypes: ['int', 'float'],           defaultParams: { min: 0, max: 100, step: 1 } },
    enum:       { label: 'Dropdown',         baseTypes: ['int', 'string'],          defaultParams: { options: {} } },
    toggle:     { label: 'Toggle Switch',    baseTypes: ['int'],                    defaultParams: {} },
    color:      { label: 'Color Picker',     baseTypes: ['int'],                    defaultParams: { format: 'argb' } },
    tags:       { label: 'Tag Selector',     baseTypes: ['array'],                  defaultParams: { options: [] } },
    image:      { label: 'Image Preview',    baseTypes: ['string'],                 defaultParams: { accept: '.png,.jpg,.jpeg' } },
    audio:      { label: 'Audio Player',     baseTypes: ['string'],                 defaultParams: { accept: '.mp3,.wav,.ogg' } },
    file:       { label: 'File Picker',      baseTypes: ['string'],                 defaultParams: { accept: '' } },
    '2dani':    { label: '2D Animation',     baseTypes: ['string'],                 defaultParams: {} },
    isometric:  { label: 'Isometric Grid',   baseTypes: ['array'],                  defaultParams: { max_x: 8, max_y: 8 } },
    ref:        { label: 'Entity Reference', baseTypes: ['int'],                    defaultParams: { category: '' } },
    date:       { label: 'Date Picker',      baseTypes: ['string'],                 defaultParams: {} },
    list:       { label: 'List Editor',      baseTypes: ['array'],                  defaultParams: {} },
    struct:     { label: 'Struct Container', baseTypes: ['array'],                  defaultParams: {} },
    json:       { label: 'JSON Editor',      baseTypes: ['int', 'float', 'string', 'array'], defaultParams: {} },
};

// ── Card slots ──

export const CARD_SLOTS = {
    thumbnail: { label: 'Thumbnail',  capacity: 1,    position: 'top' },
    title:     { label: 'Title',      capacity: 1,    position: 'header' },
    subtitle:  { label: 'Subtitle',   capacity: 1,    position: 'header' },
    info:      { label: 'Info',       capacity: 'multi', position: 'body' },
    badges:    { label: 'Badges',     capacity: 'multi', position: 'footer' },
    accent:    { label: 'Accent',     capacity: 1,    position: 'border' },
};

export const CARD_SLOT_NAMES = Object.keys(CARD_SLOTS);

// ── Helpers ──

export function isBaseType(name) {
    return name in BASE_TYPES;
}

export function getBaseTypeDefault(name) {
    return BASE_TYPES[name]?.default ?? null;
}

export function getCompatibleUIs(baseTypeName) {
    return Object.entries(UI_COMPONENTS)
        .filter(([, def]) => def.baseTypes.includes(baseTypeName))
        .map(([key, def]) => ({ key, ...def }));
}
