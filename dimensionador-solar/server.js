// ═══════════════════════════════════════════════════════════════
// SERVIDOR PROXY - Dimensionador Solar RV Energía
// Este archivo es el "puente" entre la app y la IA de Anthropic
// ═══════════════════════════════════════════════════════════════

const http = require('http');
const fs = require('fs');
const path = require('path');

// ┌─────────────────────────────────────────────────────────────┐
// │  CONFIGURACIÓN - Acá va tu API Key de Anthropic             │
// │  Podés ponerla acá directamente o como variable de entorno  │
// └─────────────────────────────────────────────────────────────┘
const API_KEY = process.env.ANTHROPIC_API_KEY || 'TU-API-KEY-ACA';
const PORT = process.env.PORT || 3000;

if (API_KEY === 'TU-API-KEY-ACA') {
  console.log('\n⚠️  ¡ATENCIÓN! Necesitás configurar tu API Key de Anthropic.');
  console.log('   Editá server.js y reemplazá "TU-API-KEY-ACA" por tu key.');
  console.log('   O ejecutá: set ANTHROPIC_API_KEY=tu-key-aca (Windows)');
  console.log('              export ANTHROPIC_API_KEY=tu-key-aca (Mac/Linux)\n');
}

const server = http.createServer(async (req, res) => {
  // ── CORS headers (permite que la app hable con el server) ──
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // ── Servir la app (archivos HTML, CSS, JS, imágenes) ──
  if (req.method === 'GET') {
    let filePath = req.url === '/' ? '/index.html' : req.url;
    filePath = path.join(__dirname, filePath);

    const ext = path.extname(filePath);
    const mimeTypes = {
      '.html': 'text/html',
      '.js': 'application/javascript',
      '.css': 'text/css',
      '.png': 'image/png',
      '.jpg': 'image/jpeg',
      '.svg': 'image/svg+xml',
      '.ico': 'image/x-icon',
    };

    try {
      const content = fs.readFileSync(filePath);
      res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'text/plain' });
      res.end(content);
    } catch (e) {
      res.writeHead(404);
      res.end('Archivo no encontrado');
    }
    return;
  }

  // ── Proxy a la API de Anthropic ──
  if (req.method === 'POST' && req.url === '/api/analyze') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', async () => {
      try {
        const payload = JSON.parse(body);

        // Llamar a Anthropic
        const https = require('https');
        const apiBody = JSON.stringify({
          model: payload.model || 'claude-sonnet-4-20250514',
          max_tokens: payload.max_tokens || 2000,
          messages: payload.messages,
        });

        const apiRes = await new Promise((resolve, reject) => {
          const apiReq = https.request({
            hostname: 'api.anthropic.com',
            path: '/v1/messages',
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'x-api-key': API_KEY,
              'anthropic-version': '2023-06-01',
              'Content-Length': Buffer.byteLength(apiBody),
            },
          }, (apiResponse) => {
            let data = '';
            apiResponse.on('data', chunk => { data += chunk; });
            apiResponse.on('end', () => {
              resolve({ status: apiResponse.statusCode, body: data });
            });
          });
          apiReq.on('error', reject);
          apiReq.write(apiBody);
          apiReq.end();
        });

        res.writeHead(apiRes.status, { 'Content-Type': 'application/json' });
        res.end(apiRes.body);

      } catch (e) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: { message: e.message } }));
      }
    });
    return;
  }

  res.writeHead(404);
  res.end('Ruta no encontrada');
});

server.listen(PORT, () => {
  console.log(`\n🔆 ═══════════════════════════════════════════════════════`);
  console.log(`   Dimensionador Solar RV Energía`);
  console.log(`   ─────────────────────────────────────────────────────`);
  console.log(`   ✅ Servidor corriendo en: http://localhost:${PORT}`);
  console.log(`   📋 Abrí esa dirección en tu navegador`);
  console.log(`   🛑 Para detener: Ctrl+C`);
  console.log(`═══════════════════════════════════════════════════════\n`);
});
