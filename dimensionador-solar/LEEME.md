# ═══════════════════════════════════════════════════════════
# 🔆 DIMENSIONADOR SOLAR RV ENERGÍA
# Manual de instalación — Paso a paso
# ═══════════════════════════════════════════════════════════


## ¿QUÉ HAY EN ESTA CARPETA?

  📁 dimensionador-solar/
  ├── index.html    ← La app (lo que ve el usuario)
  ├── server.js     ← El servidor (el "puente" a la IA)
  └── LEEME.md      ← Este manual


## PASO 1: INSTALAR NODE.JS

Node.js es un programa gratuito que permite correr servidores web.
Descargalo de: https://nodejs.org

  → Bajá la versión LTS (la verde, la "recomendada")
  → Instalá con las opciones por defecto (siguiente, siguiente, siguiente)
  → Reiniciá la computadora después de instalar

Para verificar que se instaló bien:
  → Abrí la terminal (CMD en Windows, Terminal en Mac)
  → Escribí: node --version
  → Tiene que aparecer algo como: v20.x.x o v22.x.x


## PASO 2: OBTENER UNA API KEY DE ANTHROPIC

La API Key es como una "contraseña" que te permite usar la IA de 
Anthropic desde tu app. Tiene un costo por uso (centavos por factura
escaneada).

  1. Entrá a: https://console.anthropic.com
  2. Creá una cuenta o iniciá sesión
  3. Andá a "API Keys" en el menú lateral
  4. Hacé clic en "Create Key"
  5. Copiá la key (empieza con "sk-ant-...")
  
  ⚠️  IMPORTANTE: Guardá la key en un lugar seguro. 
      No la compartas con nadie.


## PASO 3: CONFIGURAR LA API KEY

Abrí el archivo "server.js" con cualquier editor de texto
(Notepad, TextEdit, VS Code, lo que tengas).

Buscá esta línea (está casi al principio):

  const API_KEY = process.env.ANTHROPIC_API_KEY || 'TU-API-KEY-ACA';

Reemplazá TU-API-KEY-ACA por tu key real:

  const API_KEY = process.env.ANTHROPIC_API_KEY || 'sk-ant-api03-xxxxx...';

Guardá el archivo.


## PASO 4: ARRANCAR EL SERVIDOR

  1. Abrí la terminal (CMD en Windows, Terminal en Mac)
  2. Navegá a la carpeta del proyecto:
  
     Windows:  cd C:\Users\TuNombre\Downloads\dimensionador-solar
     Mac:      cd ~/Downloads/dimensionador-solar
     
     (Ajustá la ruta a donde tengas la carpeta)
     
  3. Ejecutá:
  
     node server.js
     
  4. Vas a ver este mensaje:
  
     🔆 ═══════════════════════════════════════════════════════
        Dimensionador Solar RV Energía
        ✅ Servidor corriendo en: http://localhost:3000
        📋 Abrí esa dirección en tu navegador
     ═══════════════════════════════════════════════════════


## PASO 5: USAR LA APP

  1. Abrí tu navegador (Chrome, Firefox, Edge)
  2. Entrá a: http://localhost:3000
  3. ¡Listo! La app funciona con el scanner de facturas activado.
  4. Subí una factura en PDF o foto y la IA la va a leer.


## PARA DETENER EL SERVIDOR

  → En la terminal donde lo arrancaste, presioná Ctrl+C


## PARA VOLVER A ARRANCAR

  → Repetí el Paso 4 (abrir terminal, ir a la carpeta, node server.js)


## PREGUNTAS FRECUENTES

  P: ¿Cuánto cuesta usar la API?
  R: Aprox. USD 0.01-0.03 por cada factura escaneada (centavos).
     Podés ver tu consumo en https://console.anthropic.com
     
  P: ¿Puedo publicar la app en internet?
  R: Sí, podés subirla a servicios como Railway, Render, o Vercel.
     Pero necesitás configurar la API Key como variable de entorno
     (no dejarla en el código).
     
  P: ¿Funciona sin internet?
  R: La app se abre, pero el scanner de facturas necesita internet
     para llamar a la IA. Los otros modos (electrodomésticos, manual)
     funcionan sin internet.

  P: ¿Puedo compartir la URL con clientes?
  R: Si lo corrés en tu compu, solo funciona en tu red local.
     Para que otros accedan, necesitás publicarlo en un servidor.


## SOPORTE

  Si tenés problemas, contactanos:
  ✉️  info@rvenergia.com.ar
  📱  +54 (11) 5140-6628
  🌐  www.rvenergia.com.ar
