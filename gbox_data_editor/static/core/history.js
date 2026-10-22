/**
 * history.js — Undo/Redo operation stack with debounce-aware recording.
 */

const MAX_HISTORY = 50;

export class HistoryManager {
    constructor(onApply) {
        this._stack = [];
        this._cursor = -1;
        this._onApply = onApply; // callback(action) to apply undo/redo
    }

    /**
     * Record a new operation.
     * @param {string} label - Human-readable description
     * @param {object} undoAction - Data to restore previous state
     * @param {object} redoAction - Data to apply new state
     */
    push(label, undoAction, redoAction) {
        // Truncate any redo history beyond cursor
        this._stack = this._stack.slice(0, this._cursor + 1);
        this._stack.push({ label, undo: undoAction, redo: redoAction, time: Date.now() });
        // Trim to max size
        if (this._stack.length > MAX_HISTORY) {
            this._stack.shift();
        }
        this._cursor = this._stack.length - 1;
    }

    undo() {
        if (this._cursor < 0) return false;
        const entry = this._stack[this._cursor];
        this._onApply(entry.undo);
        this._cursor--;
        return true;
    }

    redo() {
        if (this._cursor >= this._stack.length - 1) return false;
        this._cursor++;
        const entry = this._stack[this._cursor];
        this._onApply(entry.redo);
        return true;
    }

    /**
     * Jump to a specific index in the history.
     */
    jumpTo(index) {
        if (index < -1 || index >= this._stack.length) return;
        while (this._cursor > index) {
            this.undo();
        }
        while (this._cursor < index) {
            this.redo();
        }
    }

    get canUndo() { return this._cursor >= 0; }
    get canRedo() { return this._cursor < this._stack.length - 1; }
    get cursor() { return this._cursor; }
    get entries() { return this._stack; }

    clear() {
        this._stack = [];
        this._cursor = -1;
    }

    toJSON() {
        return { stack: this._stack, cursor: this._cursor };
    }

    fromJSON(data) {
        if (data?.stack) {
            this._stack = data.stack;
            this._cursor = data.cursor ?? this._stack.length - 1;
        }
    }
}
