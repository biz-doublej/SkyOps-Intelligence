/**
 * WebSocket URL helper — keeps the connection on the same origin as the
 * Dashboard page so that Next.js rewrites can proxy /ws/* to api:8000.
 *
 * Behaviour:
 *  - Browser: ws://<host>:<port> or wss://<host>:<port> matching page scheme
 *  - SSR: returns "" (WebSocket is not used server-side)
 *  - Override: set NEXT_PUBLIC_WS_URL at build time to pin a specific host
 */
export function getWsOrigin(): string {
  const override = process.env.NEXT_PUBLIC_WS_URL;
  if (override && override !== "") return override;
  if (typeof window === "undefined") return "";
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}`;
}
