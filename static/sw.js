// Service worker do PWA: guarda a "casca" do app para abrir rápido e mostrar uma página offline.
// Ao alterar arquivos do app, aumente a versão para descartar o cache antigo.
const VERSAO_CACHE = 'chromebooks-v1';

const ARQUIVOS_APP = [
    '/static/style.css',
    '/static/script.js',
    '/static/offline.html',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'
];

self.addEventListener('install', evento => {
    evento.waitUntil(
        caches.open(VERSAO_CACHE)
            .then(cache => cache.addAll(ARQUIVOS_APP))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', evento => {
    evento.waitUntil(
        caches.keys()
            .then(nomes => Promise.all(nomes.filter(nome => nome !== VERSAO_CACHE).map(nome => caches.delete(nome))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', evento => {
    const requisicao = evento.request;
    if (requisicao.method !== 'GET') return;

    const url = new URL(requisicao.url);

    // A API nunca passa pelo cache: dados de agendamento precisam estar sempre atualizados
    if (url.origin === self.location.origin && url.pathname.startsWith('/api/')) return;

    // Páginas: tenta a rede e, sem conexão, mostra a página offline
    if (requisicao.mode === 'navigate') {
        evento.respondWith(
            fetch(requisicao).catch(() => caches.match('/static/offline.html'))
        );
        return;
    }

    // Arquivos estáticos: responde do cache e atualiza em segundo plano
    if (ARQUIVOS_APP.includes(url.href) || ARQUIVOS_APP.includes(url.pathname)) {
        evento.respondWith(
            caches.open(VERSAO_CACHE).then(cache =>
                cache.match(requisicao).then(emCache => {
                    const daRede = fetch(requisicao)
                        .then(resposta => {
                            if (resposta.ok) cache.put(requisicao, resposta.clone());
                            return resposta;
                        })
                        .catch(() => emCache);
                    return emCache || daRede;
                })
            )
        );
    }
});
