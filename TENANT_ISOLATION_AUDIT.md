# Tenant Isolation Audit

Fecha: `2026-04-04`

## Objetivo
Confirmar qué parte del aislamiento multi-tenant ya está cerrada, qué parte sigue global por diseño y qué puntos pasan al siguiente sprint sin mezclarlos.

## Estado

### Hecho
- `venues`, `courts`, `timeslots`, `bookings` y `admin` operativo filtran por `organization_id`.
- `organizations/current`, `settings`, invitaciones y staff quedan scopeados al complejo actual.
- Los flujos de alta operativa persisten `organization_id` en registros core.
- Existe auditoría técnica en `GET /admin/tenant-integrity`.
- Hay tests cruzados para:
  - admin de tenant A no puede gestionar recursos de tenant B
  - staff de tenant A no puede operar canchas de tenant B
  - user de tenant A no puede reservar turnos de tenant B

### Parcial
- `sports` sigue siendo catálogo global.
  - No es una fuga de datos.
  - Sí es una decisión de producto/arquitectura todavía abierta.
- `auth/register` y `get_request_organization()` todavía resuelven al tenant por defecto (`complejo-demo`) cuando no hay contexto público explícito.
  - No rompe aislamiento autenticado.
  - Sí limita la experiencia SaaS pública.

### Falta
- Resolver tenant público por `slug` o subdominio.
- Definir estrategia final para deportes:
  - catálogo global
  - deportes por complejo
  - modelo híbrido
- Revisar scripts operativos para clasificar cuáles son intencionalmente globales.

## Hallazgos concretos

### Rutas operativas correctamente aisladas
- `app/api/routes/venues.py`
- `app/api/routes/courts.py`
- `app/api/routes/timeslots.py`
- `app/api/routes/bookings.py`
- `app/api/routes/admin.py` para métricas, bulk de turnos y usuarios
- `app/api/routes/organizations.py` para gestión del complejo actual

### Globales por diseño actual
- `app/api/routes/sports.py`
- fallback de tenant por defecto en:
  - `app/api/routes/auth.py`
  - `app/api/deps/auth.py`

### Scripts
- `scripts/reset_app_data.py` es global y destructivo a propósito.
  - Está bien para entorno local/admin.
  - No debe exponerse como operación normal de tenant.

## Conclusión
`S1 Tenant Isolation Audit` queda funcionalmente cerrado para los recursos operativos críticos.

Lo siguiente no es “arreglar fugas”, sino resolver decisiones de producto:
1. `S2 Sports Strategy`
2. `S3 Public Tenant Resolution`
