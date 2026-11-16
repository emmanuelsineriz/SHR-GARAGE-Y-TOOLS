/* Service worker de SHR Garage & Tools · Ventas.
   El número de versión se reemplaza al compilar (APP_VERSION) para que cada
   versión nueva limpie la caché vieja. */
const VERSION='2.4.1';
const CACHE='shr-ventas-'+VERSION;
const SHELL=['./','./index.html','./manifest.webmanifest','./icons/icon-192.png','./icons/icon-512.png','./icons/icon-512-maskable.png','./icons/icon-180.png'];

self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k.startsWith('shr-ventas-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',e=>{
  const req=e.request;
  if(req.method!=='GET')return;
  const url=new URL(req.url);
  if(url.origin==='https://www.gstatic.com'&&url.pathname.startsWith('/firebasejs/')){   // librerías de Firebase: se guardan para que ande con mala señal
    e.respondWith(caches.match(req).then(hit=>hit||fetch(req).then(r=>{if(r.ok){const cp=r.clone();caches.open(CACHE).then(c=>c.put(req,cp))}return r})));
    return;
  }
  if(url.origin!==location.origin)return;            // fotos de elgasolero: las maneja el navegador
  if(/\/(catalogo|estado)\.json$/.test(url.pathname)){      // datos que cambian a diario: primero red, si no hay internet, el último guardado
    e.respondWith(fetch(req,{cache:'no-cache'}).then(r=>{if(r.ok){const cp=r.clone();caches.open(CACHE).then(c=>c.put(req,cp))}return r}).catch(()=>caches.match(req)));
    return;
  }
  if(req.mode==='navigate'){                          // la app: primero red (versión nueva), si no hay internet, caché
    e.respondWith(fetch(req).then(r=>{const cp=r.clone();caches.open(CACHE).then(c=>c.put('./index.html',cp));return r}).catch(()=>caches.match('./index.html').then(r=>r||caches.match('./'))));
    return;
  }
  e.respondWith(caches.match(req).then(hit=>hit||fetch(req).then(r=>{if(r.ok){const cp=r.clone();caches.open(CACHE).then(c=>c.put(req,cp))}return r})));
});
