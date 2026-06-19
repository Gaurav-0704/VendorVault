# Gaurav Singh Thakur — MIT License
#
# PWA plumbing — manifest, service worker, and icon serving.
# This is what lets me install the app on my phone's home screen.

import json
import os
import socket
from flask import Blueprint, Response, send_from_directory

pwa_bp = Blueprint('pwa', __name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PORT = int(os.environ.get('PORT', 5000))


def _local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return '127.0.0.1'


@pwa_bp.route('/manifest.json')
def manifest():
    data = {
        "name": "VendorVault",
        "short_name": "VendorVault",
        "description": "Sales & Profit Tracking for Small Businesses",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#6366f1",
        "orientation": "portrait-primary",
        "icons": [
            {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
        "categories": ["business", "finance", "productivity"],
        "screenshots": [],
    }
    return Response(json.dumps(data), mimetype='application/manifest+json')


@pwa_bp.route('/sw.js')
def service_worker():
    """Simple service worker — network-first for API calls, cache-first for static assets."""
    sw_code = """
const CACHE_NAME = 'vendorvault-v1';
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;

    if (event.request.url.includes('/api/')) {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
                    return response;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then(cached => cached || fetch(event.request))
    );
});
"""
    return Response(sw_code, mimetype='application/javascript')


@pwa_bp.route('/static/icons/<path:filename>')
def serve_icon(filename):
    icons_dir = os.path.join(_BASE_DIR, 'static', 'icons')
    return send_from_directory(icons_dir, filename)
