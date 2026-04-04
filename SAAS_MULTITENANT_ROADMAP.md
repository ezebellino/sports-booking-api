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

### A revisar o terminar
- Decisión final sobre catálogo de deportes.
- Resolución pública del tenant en la experiencia web.
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
- Las excepciones actuales quedaron clasificadas como decisiones de producto (`sports` global y tenant público por resolver), no como fugas.

## Phase S2: Sports Strategy
Objetivo: definir si los deportes son globales o por complejo.

### Opción recomendada
Mantener catálogo global de deportes base y permitir activación/configuración por complejo.

### Task S2.1
Decidir modelo final:
- catálogo global
- deportes por tenant
- híbrido

### Task S2.2
Implementar el modelo elegido sin romper políticas por deporte.

### Definition of Done
- Queda claro qué puede configurar cada complejo respecto a deportes.

## Phase S3: Public Tenant Resolution
Objetivo: hacer que cada complejo tenga una entrada pública clara.

### Recomendación
Arrancar con `slug` por path y después evaluar subdominios.

Ejemplo:
- `reservas-deportivas.com/blackpadel`

### Task S3.1
Definir estrategia pública:
- path por slug
- subdominio

### Task S3.2
Hacer que login, registro y home pública se resuelvan por tenant visible.

### Definition of Done
- El usuario entiende claramente en qué complejo está operando antes de iniciar sesión.

## Phase S4: Real Branding
Objetivo: que el tenant no sea solo un dato técnico, sino una experiencia visible.

### Task S4.1
Aplicar branding del complejo en:
- header
- login
- registro
- home pública
- panel admin

### Task S4.2
Usar:
- `branding_name`
- `logo_url`
- `primary_color`

### Definition of Done
- Cada complejo se percibe visualmente como su propio espacio dentro de la plataforma.

## Phase S5: Staff Permissions
Objetivo: refinar permisos operativos.

### Roles sugeridos
- `admin`
- `staff_operations`
- `staff_metrics`
- `user`

### Task S5.1
Definir matriz de permisos.

### Task S5.2
Ajustar backend y frontend según esa matriz.

### Definition of Done
- El staff no recibe más acceso del necesario.

## Phase S6: SaaS Operations
Objetivo: preparar la plataforma para clientes reales.

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
1. S2 Sports Strategy
2. S3 Public Tenant Resolution
3. S4 Real Branding
4. S5 Staff Permissions
5. S6 SaaS Operations

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

Así conservamos contexto técnico y producto sin mezclar pasado con próximos pasos.
