# Copyright (c) 2026 Gaurav Singh Thakur. All rights reserved.

import json
from flask import Blueprint, Response, send_from_directory
import os
import config

pwa_bp = Blueprint('pwa', __name__)


@pwa_bp.route('/manifest.json')
def manifest():
    """Serve the PWA manifest for mobile app installation."""
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
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
        ],
        "categories": ["business", "finance", "productivity"],
        "screenshots": []
    }
    return Response(json.dumps(data), mimetype='application/manifest+json')


@pwa_bp.route('/sw.js')
def service_worker():
    """Serve the service worker from root scope."""
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

    // Network-first for API calls
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

    // Cache-first for static assets
    event.respondWith(
        caches.match(event.request).then(cached => cached || fetch(event.request))
    );
});
"""
    return Response(sw_code, mimetype='application/javascript')


@pwa_bp.route('/static/icons/<path:filename>')
def serve_icon(filename):
    """Serve PWA icon files."""
    icons_dir = os.path.join(config.BASE_DIR, 'static', 'icons')
    return send_from_directory(icons_dir, filename)


@pwa_bp.route('/api/network-info')
def network_info():
    """Return the local IP address for WiFi connection sharing."""
    local_ip = config.get_local_ip()
    return {
        'ip': local_ip,
        'port': config.PORT,
        'url': f'http://{local_ip}:{config.PORT}'
    }
