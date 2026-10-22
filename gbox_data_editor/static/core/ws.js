/**
 * ws.js — WebSocket connection manager with auto-reconnect.
 */

export class WsManager {
    constructor(onMessage, onStatusChange) {
        this._onMessage = onMessage;
        this._onStatusChange = onStatusChange;
        this._ws = null;
        this._reconnectTimer = null;
        this._connected = false;
    }

    connect() {
        if (this._ws) return;
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${proto}//${location.host}/ws`;
        this._ws = new WebSocket(url);

        this._ws.onopen = () => {
            this._connected = true;
            this._onStatusChange(true);
        };

        this._ws.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                this._onMessage(msg);
            } catch (e) {
                console.error('WS parse error:', e);
            }
        };

        this._ws.onclose = () => {
            this._ws = null;
            this._connected = false;
            this._onStatusChange(false);
            this._scheduleReconnect();
        };

        this._ws.onerror = () => {
            this._ws?.close();
        };
    }

    _scheduleReconnect() {
        if (this._reconnectTimer) return;
        this._reconnectTimer = setTimeout(() => {
            this._reconnectTimer = null;
            this.connect();
        }, 2000);
    }

    get connected() {
        return this._connected;
    }

    destroy() {
        clearTimeout(this._reconnectTimer);
        this._ws?.close();
    }
}
