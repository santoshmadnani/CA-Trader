/* CA Trader service worker: shows signal-alert push notifications and opens the app when one is tapped.
   It does no caching, so the app always loads fresh from the server. Served at /sw.js for root scope. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch { d = { title: "CA Trader", body: e.data ? e.data.text() : "" }; }
  e.waitUntil(self.registration.showNotification(d.title || "CA Trader", {
    body: d.body || "", tag: d.tag || undefined, renotify: !!d.tag, requireInteraction: false,
    icon: "/static/m/icon-192.png", badge: "/static/m/icon-192.png", data: { url: d.url || "/terminal?ui=mobile" },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || "/terminal?ui=mobile", self.location.origin).href;
  e.waitUntil((async () => {
    const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const w of wins) { if (new URL(w.url).origin === self.location.origin) { await w.focus(); try { w.postMessage({ type: "open-signals" }); } catch { /* ignore */ } return; } }
    await self.clients.openWindow(url);
  })());
});
