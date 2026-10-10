#!/bin/sh
# Comprueba un despliegue completo (HU-01): API en Render, web en Vercel y CORS entre las dos.
#
#   sh scripts/smoke-deploy.sh https://restoapi.onrender.com https://restoapi.vercel.app
#
# Sale con código 1 si falla alguna comprobación. La primera petición puede tardar
# hasta un minuto si Render está dormido (cold start del plan free).

API=${1%/}
WEB=${2%/}
if [ -z "$API" ] || [ -z "$WEB" ]; then
  echo "Uso: sh scripts/smoke-deploy.sh <URL_API_RENDER> <URL_WEB_VERCEL>"
  exit 2
fi

fallos=0
ok() { echo "  OK    $1"; }
ko() { echo "  FALLO $1"; fallos=$((fallos + 1)); }
status() { curl -s -o /dev/null -w '%{http_code}' --max-time "${2:-20}" "$1"; }

echo "API: $API"

# Render free se duerme tras 15 min: se reintenta /health hasta 2 minutos
for i in 1 2 3 4 5 6; do
  health=$(curl -fsS --max-time 30 "$API/health" 2>/dev/null) && break
  echo "  ...   esperando a que Render despierte ($i/6)"
  sleep 10
done
if [ -n "$health" ]; then ok "/health → $health"; else ko "/health no responde"; fi

[ "$(status "$API/docs")" = "200" ] && ok "/docs (Swagger) → 200" || ko "/docs no responde 200"

# Sin token, una ruta protegida debe dar 401 (la API está viva y aplica la auth)
[ "$(status "$API/users/")" = "401" ] && ok "/users/ sin token → 401" || ko "/users/ sin token no da 401"

# CORS: el navegador hace un preflight desde la URL de Vercel; la API debe devolverla en Allow-Origin
allow=$(curl -s -o /dev/null -D - --max-time 20 -X OPTIONS "$API/health" \
  -H "Origin: $WEB" -H "Access-Control-Request-Method: GET" |
  tr -d '\r' | grep -i '^access-control-allow-origin:' | cut -d' ' -f2)
if [ "$allow" = "$WEB" ]; then
  ok "CORS permite $WEB"
else
  ko "CORS no permite $WEB (ALLOWED_ORIGINS en Render debe incluirla exacta, sin / final)"
fi

echo "Web: $WEB"

[ "$(status "$WEB/")" = "200" ] && ok "/ → 200" || ko "/ no responde 200"
# Ruta del SPA: sin el rewrite de vercel.json daría 404
[ "$(status "$WEB/login")" = "200" ] && ok "/login (rewrite del SPA) → 200" || ko "/login no responde 200"

# VITE_API_URL se fija al construir: el JS publicado debe apuntar a la API de Render
js=$(curl -s --max-time 20 "$WEB/" | grep -o '/assets/index-[^"]*\.js' | head -1)
if [ -n "$js" ] && curl -s --max-time 20 "$WEB$js" | grep -q "$API"; then
  ok "el frontend apunta a $API"
else
  ko "el frontend no apunta a $API (revisar VITE_API_URL en Vercel y volver a desplegar)"
fi

echo
if [ "$fallos" -eq 0 ]; then
  echo "Despliegue correcto."
else
  echo "$fallos comprobación(es) fallida(s)."
  exit 1
fi
