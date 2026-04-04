"use client";
import { useEffect, useRef, useCallback, useState } from "react";

interface UseWebSocketOptions {
  url: string;
  onMessage: (data: unknown) => void;
  enabled?: boolean;
}

export function useWebSocket({ url, onMessage, enabled = true }: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const retryDelay = useRef(1000);

  const connect = useCallback(() => {
    if (!enabled) return;
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        setConnected(true);
        retryDelay.current = 1000;
      };
      ws.onmessage = (e) => {
        try { onMessage(JSON.parse(e.data)); } catch {}
      };
      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, Math.min(retryDelay.current, 30000));
        retryDelay.current *= 2;
      };
      ws.onerror = () => ws.close();
    } catch {
      setTimeout(connect, retryDelay.current);
    }
  }, [url, onMessage, enabled]);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  return { connected };
}
