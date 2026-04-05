# Railway Deploy Plan

## Objetivo
Subir `sports-booking` a Railway con una arquitectura SaaS razonable para producción inicial, sin romper el flujo multi-tenant ya implementado.

## Estado actual del repo
- Backend: FastAPI en [app/main.py](c:/ProjectsZeqe/sports-booking/app/main.py)
- Frontend: Vite + React en [frontend/package.json](c:/ProjectsZeqe/sports-booking/frontend/package.json)
- Base local actual: Postgres por `docker-compose`
- Assets de logo: filesystem local bajo `uploads/`
- Email: SMTP configurable por `.env`
- WhatsApp: configurable por tenant

## Estado actual en Railway
- Railway CLI autenticado
- Proyecto reutilizable confirmado: `Sports-Booking`
- Project ID: `0de1e7d6-430f-4d69-8eed-a9414336feb6`
- Environment: `production`
- Environment ID: `182e9638-2364-4116-a4da-57c1b1afe354`
- Servicio backend existente: `sports-booking-api`
- Service ID: `dcddc2f1-8c70-45d8-b3f2-1cf1450b8696`
- Repo actualmente conectado a ese servicio: `ezebellino/sports-booking-api`
- Último deployment registrado en Railway: `FAILED`

## Arquitectura recomendada en Railway
Usar un solo proyecto Railway llamado `Sports-Booking`, con estos servicios:

1. `sports-booking-api`
- Servicio Python
- Root: repo raíz
- Archivos ya preparados en este repo:
  - [requirements.txt](c:/ProjectsZeqe/sports-booking/requirements.txt)
  - [Procfile](c:/ProjectsZeqe/sports-booking/Procfile)
  - [scripts/railway-backend-start.sh](c:/ProjectsZeqe/sports-booking/scripts/railway-backend-start.sh)
  - [scripts/railway-backend-predeploy.sh](c:/ProjectsZeqe/sports-booking/scripts/railway-backend-predeploy.sh)
- Start command efectivo:
```bash
bash scripts/railway-backend-start.sh
```

2. `frontend`
- Servicio Node para compilar y servir `frontend/dist`
- Root: `frontend`
- Archivos ya preparados en este repo:
  - [frontend/package.json](c:/ProjectsZeqe/sports-booking/frontend/package.json)
  - [frontend/Procfile](c:/ProjectsZeqe/sports-booking/frontend/Procfile)
- Build command:
```bash
npm install && npm run build
```
- Start command:
```bash
npm run start
```

3. `Postgres`
- Base administrada por Railway
- `DATABASE_URL` inyectada al backend

4. `Object Storage` externo
- Recomendado: Cloudflare R2 o S3-compatible
- No conviene dejar logos en filesystem local del contenedor

## Decisiones de despliegue

### Backend
Se puede desplegar ya.

Requisitos:
- usar `DATABASE_URL` de Railway
- correr migraciones con predeploy command:
```bash
bash scripts/railway-backend-predeploy.sh
```
- configurar `FRONTEND_ORIGINS` y `FRONTEND_PUBLIC_URL`
- el servicio debe apuntar a este repo actual, no al repo viejo `ezebellino/sports-booking-api`

### Frontend
También se puede desplegar en Railway, pero hay una nota práctica:
- Vite genera estáticos
- Railway no es un hosting estático puro
- para una primera versión sirve `vite preview` como servidor de estáticos del build

Más adelante, si querés optimizar costo/simplicidad:
- frontend en Cloudflare Pages / Vercel / Netlify
- backend y Postgres en Railway

### Media / logos
No dejar `uploads/` como solución final en Railway.

Razón:
- el filesystem del servicio no es persistencia confiable para assets
- redeploys o reemplazos de contenedor pueden perder archivos

Plan:
1. primer deploy: puede seguir local si querés solo probar end-to-end
2. deploy serio: migrar `app/core/logo_storage.py` a storage externo

## Variables de entorno necesarias

Archivos guía ya preparados en el repo:
- backend: [`.env.railway.backend.example`](c:/ProjectsZeqe/sports-booking/.env.railway.backend.example)
- frontend: [`frontend/.env.example`](c:/ProjectsZeqe/sports-booking/frontend/.env.example)

### Backend obligatorias
```env
SECRET_KEY=<generar valor largo y nuevo>
ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=30
REFRESH_TOKEN_DAYS=7
DATABASE_URL=<la provee Railway Postgres>
FRONTEND_ORIGINS=https://app.reservas-deportivas.com,https://reservas-deportivas.com
FRONTEND_PUBLIC_URL=https://app.reservas-deportivas.com
MEDIA_ROOT=uploads
MEDIA_URL_PREFIX=/media
ORGANIZATION_LOGO_DIR=organization-logos
MAX_LOGO_UPLOAD_BYTES=2097152
```

### Backend email
```env
EMAIL_PROVIDER=smtp
EMAIL_FROM=notificaciones@reservas-deportivas.com
EMAIL_FROM_NAME=Reservas Deportivas
SMTP_HOST=smtp.hostinger.com
SMTP_PORT=587
SMTP_USERNAME=notificaciones@reservas-deportivas.com
SMTP_PASSWORD=<secret real>
SMTP_USE_TLS=true
```

### Backend WhatsApp global fallback
```env
WHATSAPP_PROVIDER=disabled
WHATSAPP_API_VERSION=v23.0
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_TEMPLATE_LANGUAGE=es_AR
WHATSAPP_TEMPLATE_BOOKING_CONFIRMED=booking_confirmation
WHATSAPP_TEMPLATE_BOOKING_CANCELLED=booking_cancellation
WHATSAPP_RECIPIENT_OVERRIDE=
```

### Frontend
```env
VITE_API_URL=https://api.reservas-deportivas.com
```

## Variables que NO deben seguir igual que en local
- `SECRET_KEY`
- `DATABASE_URL`
- `SMTP_PASSWORD`
- cualquier token de WhatsApp

## Dominios recomendados
Asumiendo que tu web comercial ya vive en `reservas-deportivas.com`:

- landing comercial:
  - `https://reservas-deportivas.com`
- app SaaS:
  - `https://app.reservas-deportivas.com`
- API:
  - `https://api.reservas-deportivas.com`

Esto evita mezclar marketing, frontend app y backend en el mismo host.

## Orden de despliegue recomendado

### Fase 1: Preparación
1. Confirmar si usás el proyecto Railway existente `Sports-Booking` o crear uno nuevo limpio.
2. Agregar `.env.production` mentalmente al plan, no al repo.
3. Rotar secretos sensibles que hoy hayan quedado expuestos localmente o en capturas/chat.

### Fase 2: Backend primero
1. Reutilizar servicio `sports-booking-api`
2. Reapuntar el servicio al repo actual `ezebellino/sports-booking`
3. Root directory: repo raíz
4. Predeploy command:
```bash
bash scripts/railway-backend-predeploy.sh
```
5. Start command:
```bash
bash scripts/railway-backend-start.sh
```
6. Conectar Postgres Railway
7. Cargar variables de entorno
8. Desplegar backend
9. Verificar:
- `/health`
- login
- `/organizations/request-context`
- upload de logo
- invitación staff por email

### Fase 3: Frontend
1. Crear servicio `frontend`
2. Root directory: `frontend`
3. Build command:
```bash
npm install && npm run build
```
4. Start command:
```bash
npm run start
```
5. Setear `VITE_API_URL`
6. Desplegar
7. Verificar:
- login
- explorar
- admin
- upload de logo

### Fase 4: Dominio
1. apuntar `api.reservas-deportivas.com` al backend
2. apuntar `app.reservas-deportivas.com` al frontend
3. actualizar CORS y `FRONTEND_PUBLIC_URL`

### Fase 5: Hardening post deploy
1. migrar logos a storage externo
2. revisar logs y errores runtime
3. revisar SMTP en producción
4. probar invitación staff por mail
5. probar suspensión de complejo y auditoría

## Cambios técnicos recomendados antes del deploy real

### Alta prioridad
1. mover logos fuera del filesystem local
2. dejar un script o comando claro de migraciones en deploy
3. revisar chunk grande del frontend
4. agregar healthcheck explícito si hace falta

### Media prioridad
1. limpiar mojibake residual en pantallas admin viejas
2. evaluar servir frontend con mejor estrategia que `serve`
3. revisar warnings de bundle y code splitting

## Checklist de validación en producción
- backend levanta y responde `200` en health
- frontend carga sin errores de CORS
- registro/login funcionan
- request-context por slug funciona
- admin puede editar branding
- upload de logo funciona
- deportes por complejo funcionan
- invitaciones por email llegan
- suspensión de complejo bloquea acceso público
- auditoría muestra eventos recientes

## Recomendación pragmática
No haría deploy completo a Railway en un solo paso.

Orden correcto:
1. desplegar backend
2. validar API y migraciones
3. desplegar frontend
4. conectar dominios
5. recién después mover media a storage externo

## Próximo paso operativo
Usar el MCP de Railway para:
1. inspeccionar el proyecto `Sports-Booking`
2. decidir si reutilizamos ese proyecto o armamos uno nuevo
3. preparar backend service + Postgres + variables
