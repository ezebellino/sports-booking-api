# Organization Memberships Migration Plan

## Objective
Pasar de un modelo `1 user -> 1 organization_id` a un modelo SaaS real donde una misma cuenta pueda pertenecer a varios complejos y elegir con cuál operar.

## Current Limitation
Hoy el sistema funciona así:
- `users.organization_id` define el complejo activo y único del usuario.
- al crear un complejo nuevo, el usuario queda movido a ese `organization_id`
- no existe selector de complejo en login ni durante la sesión
- invitaciones y onboarding reescriben pertenencia en vez de sumar una nueva relación

Ese modelo sirve para single-membership, pero no para un SaaS multi-complejo real.

## Target Model

### New table
`organization_memberships`

Campos propuestos:
- `id`
- `user_id`
- `organization_id`
- `role`
- `is_default`
- `created_at`
- `updated_at`

Restricciones sugeridas:
- `unique(user_id, organization_id)`
- índice por `user_id`
- índice por `organization_id`
- opcional: garantizar un solo `is_default=true` por usuario

### Transitional compatibility
Durante la migración:
- `users.organization_id` se mantiene como compatibilidad temporal
- la fuente real de autorización pasa gradualmente a `organization_memberships`
- luego `users.organization_id` queda como derivado o se elimina

## Migration Strategy

### Phase M1: Schema foundation
1. Crear modelo `OrganizationMembership`.
2. Crear migración Alembic.
3. Backfill:
   - por cada `user` existente, crear una membership con:
     - `organization_id = users.organization_id`
     - `role = users.role`
     - `is_default = true`

### Phase M2: Read path
1. Auth y permisos deben leer membership activa, no `users.organization_id`.
2. Agregar helpers backend:
   - listar memberships del usuario
   - resolver membership activa
   - cambiar membership activa
3. El token o la sesión deben llevar el `organization_id` activo.

### Phase M3: Onboarding and invitations
1. Crear complejo nuevo:
   - no cambiar `users.organization_id`
   - agregar una nueva membership admin para ese usuario
2. Aceptar invitaciones:
   - agregar membership para ese complejo
   - no reescribir pertenencia previa

### Phase M4: UI flow
1. Login:
   - si el usuario tiene una sola membership, entrar directo
   - si tiene varias, pedir selección de complejo
2. Shell autenticado:
   - mostrar complejo activo
   - agregar switcher de complejo

### Phase M5: Cleanup
1. Mover todas las rutas y checks de permisos a membership activa.
2. Dejar `users.organization_id` como legado temporal.
3. Cuando todo esté estable:
   - remover dependencia funcional de `users.organization_id`
   - evaluar eliminar esa columna

## Required Backend Changes
- modelo nuevo en `app/models`
- migración Alembic con backfill
- refactor de auth deps
- `auth/me` debe devolver:
  - membership activa
  - memberships disponibles
- endpoint para cambiar de complejo activo
- onboarding e invitaciones deben crear memberships

## Required Frontend Changes
- contrato de usuario/membership en `api.ts`
- selector de complejo post-login si hay múltiples memberships
- switcher de complejo en header o shell autenticado
- persistencia del complejo activo entre refreshes

## Risks
- tokens viejos sin contexto de membership
- usuarios legacy sin backfill correcto
- rutas protegidas que sigan leyendo `users.organization_id`
- onboarding moviendo usuarios entre tenants por caminos viejos

## Definition of Done
- una misma cuenta puede pertenecer a múltiples complejos
- al crear un nuevo complejo no se pierde acceso al anterior
- aceptar invitaciones suma pertenencias, no reemplaza
- el usuario puede elegir o cambiar el complejo activo
- permisos y scoping funcionan por membership activa

## Recommended Implementation Order
1. `M1` tabla + migración + backfill
2. `M2` lectura backend y auth
3. `M3` onboarding e invitaciones
4. `M4` selector y switcher en frontend
5. `M5` cleanup del modelo legado
