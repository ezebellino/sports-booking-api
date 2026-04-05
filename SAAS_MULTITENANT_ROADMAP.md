# SaaS Multi-Tenant Roadmap

## Context
- Dominio comercial principal: `reservas-deportivas.com`
- El producto ya tiene:
  - `organization`
  - `organization_id` en entidades core
  - onboarding de complejos
  - branding y settings por complejo
  - staff, admin y user
  - WhatsApp tenant-level
  - métricas tenant-level

## Objective
Cerrar el paso de "app multi-tenant funcional" a "SaaS operable y listo para crecer" sin perder foco.

## Current Status

### Ya resuelto
- Base multi-tenant implementada.
- Scoping principal por `organization_id`.
- Onboarding de nuevos complejos.
- Gestión de branding y configuración por complejo.
- Staff operativo con permisos intermedios.
- Herramientas admin para inventario, turnos, políticas, WhatsApp y métricas.
- Catálogo global de deportes con activación por complejo.
- Resolución pública inicial por `slug` en path.

### A revisar o terminar
- Branding aplicado visualmente en toda la experiencia.
- Permisos finos por tipo de staff.
- Checklist operativo SaaS.

## Phase S1: Tenant Isolation Audit
Objetivo: confirmar que no quede ninguna fuga de datos entre complejos.

Estado: `closed`

Referencia:
- [TENANT_ISOLATION_AUDIT.md](c:/ProjectsZeqe/sports-booking/TENANT_ISOLATION_AUDIT.md)

### Cierre
- Rutas operativas críticas auditadas.
- Tests cruzados entre tenants agregados.
- Las excepciones actuales quedaron clasificadas como decisiones de producto, no como fugas.

## Phase S2: Sports Strategy
Objetivo: definir si los deportes son globales o por complejo.

Estado: `closed`

### Modelo implementado
- Catálogo global de deportes.
- Activación y configuración por complejo.
- Políticas por deporte preservadas.

### Cierre
- `user` no crea deportes.
- `staff` no crea deportes.
- `admin` administra qué deportes del catálogo quedan habilitados en su complejo.
- La búsqueda pública y operativa ya consume solo los deportes habilitados del tenant.

## Phase S3: Public Tenant Resolution
Objetivo: hacer que cada complejo tenga una entrada pública clara.

Estado: `closed`

### Estrategia adoptada
- `slug` por path

Ejemplo:
- `reservas-deportivas.com/blackpadel`

### Ya implementado
- Home pública por slug.
- Login por slug.
- Registro por slug.
- Exploración pública por slug.
- Header y navegación preservan el slug.
- El frontend envía el slug actual al backend.
- `register` crea usuarios dentro del tenant público seleccionado.
- `login` bloquea cuentas que pertenecen a otro complejo.
- `request-context` devuelve `404` si el slug público no existe.
- La app muestra una pantalla de complejo no encontrado en vez de caer al tenant por defecto.

### Pendiente menor
- Evaluar si conviene redirigir automáticamente a la URL canónica del tenant después del login.
- Revisar si `accept-invite` necesita contexto visual tenant-aware adicional.

### Definition of Done
- El usuario entiende claramente en qué complejo está operando antes de iniciar sesión.
- Un slug inexistente no mezcla ni expone datos de otro complejo.

## Phase S4: Real Branding
Objetivo: que el tenant no sea solo un dato técnico, sino una experiencia visible.

Estado: `in_progress`

### Ya implementado
- `branding_name`
- `logo_url`
- `primary_color`
- upload de logo desde archivo
- contexto visual del complejo en header y shell autenticado

### Pendiente
- Aplicar el branding del complejo en:
  - login
  - registro
  - home pública
  - panel admin
- Unificar estilos visuales tenant-aware con el logo y color principal.

### Definition of Done
- Cada complejo se percibe visualmente como su propio espacio dentro de la plataforma.

## Phase S5: Staff Permissions
Objetivo: refinar permisos operativos sin complejizar el modelo antes de tiempo.

Estado: `in_progress`

### Matriz actual adoptada
- `admin`
  - `manage_organization`
  - `manage_staff`
  - `view_metrics`
  - `manage_inventory`
  - `manage_timeslots`
  - `manage_whatsapp`
- `staff`
  - `view_metrics`
  - `manage_inventory`
  - `manage_timeslots`
- `user`
  - sin permisos operativos

### Task S5.1
- Exponer `permissions` en `auth/me`.
- Hacer enforcement backend por capacidad, no solo por `role`.
- Alinear navegación y rutas admin con esos permisos.

### Task S5.2
- Evaluar si más adelante hace falta separar `staff_operations` y `staff_metrics`.
- Ocultar o mostrar módulos admin según permiso real.

### Definition of Done
- El staff no recibe más acceso del necesario.
- La UI no muestra secciones que el backend igual terminaría bloqueando.

## Phase S6: SaaS Operations
Objetivo: preparar la plataforma para clientes reales.

Estado: `pending`

### Task S6.1
Checklist de alta de nuevo complejo.

### Task S6.2
Checklist de activación operativa:
- branding
- políticas
- WhatsApp
- feriados
- sedes
- canchas
- turnos

### Task S6.3
Suspensión o desactivación de complejo.

### Task S6.4
Auditoría básica de acciones admin.

### Definition of Done
- Un complejo puede darse de alta, configurarse y salir a producción con proceso claro.

## Recommended Order
1. S4 Real Branding
2. S5 Staff Permissions
3. S6 SaaS Operations

## About Existing Plans

### `DEVELOPMENT_PLAN.md`
Está esencialmente cumplido para la etapa fundacional del producto.

### `MULTITENANT_MIGRATION_PLAN.md`
Está mayormente ejecutado en su base técnica.

## Recommendation
No borrarlos todavía.

Mejor opción:
- dejarlos en el repo como historial
- marcarlos como `completed` o `archived`
- usar este archivo como plan activo

Así conservamos contexto técnico y de producto sin mezclar pasado con próximos pasos.
