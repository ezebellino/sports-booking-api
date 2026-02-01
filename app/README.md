# 🏟️ Sports Booking API

Backend API para la gestión de reservas deportivas, pensada para complejos deportivos con múltiples sedes, canchas y turnos.
Proyecto orientado a **arquitectura escalable**, buenas prácticas y uso real de **FastAPI + PostgreSQL + Docker**.

---

## 🚀 Tech Stack

* Python 3.12
* FastAPI
* SQLAlchemy
* Alembic
* PostgreSQL
* Docker & Docker Compose
* JWT Authentication (Access & Refresh tokens)
* Pydantic v2

---

## 📌 Features

### 🔐 Autenticación

* Registro de usuarios
* Login con OAuth2 (username / password)
* JWT Access Token
* JWT Refresh Token
* Endpoint /auth/me
* Hash de contraseñas con bcrypt

### 🏢 Gestión del dominio

* Venues (sedes / complejos)
* Courts (canchas)
* Sports (deportes)
* TimeSlots (turnos disponibles)
* Bookings (reservas reales de usuarios)

### 📅 Lógica de reservas

* Separación clara entre:

  * TimeSlot → disponibilidad
  * Booking → reserva efectiva
* Validaciones de fechas (ends_at > starts_at)
* Capacidad configurable
* Precio por turno

---

## 🧠 Modelo conceptual (simplificado)
```text
Venue
└── Court
  └── TimeSlot
    └── Booking
      └── User
```
Esta separación permite escalar a:

* múltiples usuarios
* cancelaciones
* historial
* pagos
* métricas

---

## 🐳 Docker

El proyecto corre completamente en contenedores:

* PostgreSQL
* pgAdmin
* Backend FastAPI

### Levantar entorno de desarrollo

Docker:

docker compose up -d

Backend:

uvicorn app.main:app --reload

---

## ⚙️ Variables de entorno

Archivo .env (no versionado):

DATABASE_URL=postgresql+psycopg://sports_user:password@localhost:5432/sports_booking
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=30
REFRESH_TOKEN_DAYS=7

---

## 📖 Documentación interactiva

* Swagger UI:
  [http://localhost:8000/docs](http://localhost:8000/docs)

* OpenAPI JSON:
  [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 📁 Estructura del proyecto
```text
app/
├── api/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── sports.py
│   │   ├── venues.py
│   │   ├── courts.py
│   │   ├── timeslots.py
│   │   └── bookings.py
│   ├── deps.py
│   └── router.py
├── core/
│   ├── config.py
│   └── security.py
├── db/
│   ├── base.py
│   └── session.py
├── models/
├── schemas/
├── main.py
```
---

## 🧩 Decisiones de diseño

* Separación TimeSlot vs Booking para escalabilidad real
* JWT con refresh para evitar re-login constante
* Alembic para migraciones seguras
* Docker para entorno reproducible
* Pydantic v2 para validaciones explícitas

---

## 🔮 Roadmap

* Roles (admin / user)
* Cancelación de reservas
* Protección contra overbooking
* Filtros por fecha y cancha
* Pagos (MercadoPago / Stripe)
* Frontend en React

---

## 👨‍💻 Autor

Ezequiel Bellino
Backend / Fullstack Developer
Argentina

GitHub: [https://github.com/ezebellino](https://github.com/ezebellino)
Portfolio: [https://zeqebellino.com](https://zeqebellino.com)
