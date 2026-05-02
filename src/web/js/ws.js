class ReconnectingWS {
  constructor(path, onMessage) {
    this.url = `ws://${location.host}${path}`;
    this.onMessage = onMessage;
    this._delay = 1000;
    this._connect();
  }

  _connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onmessage = (e) => {
      try {
        this.onMessage(JSON.parse(e.data));
      } catch (_) {}
    };
    this.ws.onopen = () => { this._delay = 1000; };
    this.ws.onclose = () => {
      setTimeout(() => this._connect(), this._delay);
      this._delay = Math.min(this._delay * 2, 30000);
    };
    this.ws.onerror = () => this.ws.close();
  }

  close() { this.ws.close(); }
}
