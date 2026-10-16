# RestoAPI · Documentación de la API

La referencia completa e interactiva está en Swagger (`/docs`). Este documento resume el
contrato por módulo. Formatos comunes:

- **Errores:** `{"detail": str, "code": str}` en todas las respuestas de error (HU-11).
  - Validación de datos (`422`): `{"detail": "Invalid request data", "code": "validation_error",
    "errors": [{"loc": [...], "msg": str, "type": str}]}`. `errors` indica qué campo falla.
  - Error inesperado (`500`): `{"detail": "Internal server error", "code": "internal_error"}`.
  - Codes genéricos: `not_found` (404), `conflict` (409), `forbidden` (403), `unauthorized`
    (401), `method_not_allowed` (405), `unprocessable` (422 de reglas de negocio).
  - Los `422` de reglas de negocio (por ejemplo `same_password` o `redirect_uri_not_allowed`)
    solo traen `detail` y `code`, sin `errors`.
- **Listados paginados:** `{"items": [], "total": int, "page": int, "size": int}` con
  `?page` (≥ 1, por defecto 1) y `?size` (1..100, por defecto 20)
- **Autenticación:** cabecera `Authorization: Bearer <token>`. Sin token o con un token
  no válido → `401`. Rol sin permiso → `403`.
- **Modelo de datos:** diagrama entidad-relación en [`er.md`](er.md).

<!-- TODO(Rita, R-08): completar el resto de módulos. -->

## Swagger (`/docs`) · HU-26

Swagger está en `/docs`: en local, http://127.0.0.1:8000/docs, y en producción,
https://restoapi-47sp.onrender.com/docs. El esquema OpenAPI está en `/openapi.json`.

- **Authorize:** pulsa **Authorize**, escribe el email en `username` y la contraseña en
  `password`, y deja vacíos `client_id` y `client_secret`. Swagger llama a `POST /auth/login`
  y añade `Authorization: Bearer <token>` a todas las peticiones. El token no se guarda al
  recargar la página.
- **Desde otra aplicación:** `POST /auth/login` como formulario
  (`application/x-www-form-urlencoded`, `username` = email) devuelve
  `{"access_token": "...", "token_type": "bearer"}`. Envía el `access_token` en la cabecera
  `Authorization`.
- **Qué documenta cada endpoint de `/auth` y `/users`:** el rol permitido (línea `Rol: ...`
  de la descripción), ejemplos de petición y de respuesta, y cada error posible con su
  `code`. `tests/test_openapi.py` falla si un endpoint nuevo de `/auth` o `/users` llega sin
  esa documentación.

## Autenticación (`/auth`) · HU-04, HU-22, HU-38, HU-33, HU-31

| Método | Ruta | Qué hace | Éxito |
|---|---|---|---|
| `POST` | `/auth/register` | Auto-registro público de un `customer` | `201` |
| `POST` | `/auth/login` | Inicia sesión y devuelve un `AccessToken` | `200` |
| `POST` | `/auth/social/{provider}` | Login con Google o GitHub (`provider` = `google` \| `github`) | `200` |
| `POST` | `/auth/2fa/verify` | Segundo paso del login con verificación en dos pasos | `200` |
| `GET` | `/auth/me` | Datos del usuario autenticado | `200` |
| `POST` | `/auth/set-password` | Crea o restablece la contraseña con el token del email ([HU-52](#crear-la-contraseña-post-authset-password)) | `204` |
| `POST` | `/auth/verify-email` | Verifica el email con el token del email ([HU-33](#verificación-de-email-y-recuperación-de-contraseña--hu-33)) | `204` |
| `POST` | `/auth/resend-verification` | Pide otro enlace de verificación (HU-33) | `202` |
| `POST` | `/auth/forgot-password` | Pide un enlace para restablecer la contraseña (HU-33) | `202` |

### Auto-registro (`POST /auth/register`)

No requiere token. Crea la cuenta al instante (`is_active=true`); el `role` del payload se
ignora y siempre se crea un `customer` (R-03). No emite token: hay que iniciar sesión
después con `POST /auth/login`. La cuenta nace con `email_verified=false` y recibe en
segundo plano un email con el enlace de verificación (HU-33, R-15); la respuesta no cambia
y se puede iniciar sesión sin verificar.

```json
{"name": "Ana Gómez", "email": "ana@test.com", "phone": "600123456", "password": "secreto123"}
```

Respuesta `201` (`UserOut`; nunca incluye `password_hash` ni el token):

```json
{"id": 7, "name": "Ana Gómez", "email": "ana@test.com", "phone": "600123456",
 "role": "customer", "is_active": true, "email_verified": false,
 "created_at": "2026-10-14T10:15:00"}
```

- **Email único sin distinguir mayúsculas** y guardado en minúsculas (R-01): se puede
  iniciar sesión con cualquier combinación de mayúsculas/minúsculas. Duplicado → `409`.
- **Contraseña ≥ 8 caracteres** (R-02); se guarda hasheada con bcrypt.

### Iniciar sesión (`POST /auth/login`)

`application/x-www-form-urlencoded` con `username` (el email) y `password`. Devuelve
`{"access_token": "...", "token_type": "bearer"}` (`200`). Credenciales incorrectas o
usuario desactivado → `401`. No comprueba `email_verified`: una cuenta sin verificar
inicia sesión igual (HU-33, R-15).

#### Límite de intentos · HU-31 (R-10)

Los intentos fallidos se cuentan por pareja **IP + email** (el email en minúsculas y sin
espacios). Cuenta cualquier `401` del login; un `422` no cuenta.

| Situación | Respuesta |
|---|---|
| Fallos 1 a 5 en 15 minutos | `401` como siempre |
| Desde el sexto intento, hasta que pasan 15 minutos desde el primer fallo | `429` `too_many_attempts`, también con la contraseña correcta |
| Login correcto antes del bloqueo | `200`; los fallos de esa IP y ese email vuelven a 0 |
| Otra IP con el mismo email, u otro email con la misma IP | No les afecta el bloqueo |

El `429` trae la cabecera `Retry-After` con los segundos que faltan:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 812

{"detail": "Too many failed login attempts. Try again later.", "code": "too_many_attempts"}
```

Variables: `LOGIN_MAX_ATTEMPTS` (5), `LOGIN_WINDOW_MINUTES` (15) y `CLIENT_IP_HEADER`
(cabecera con la IP real; vacía en local, `True-Client-IP` en Render). Los contadores viven
en memoria: un reinicio del servidor los borra. El login social no tiene límite. El código de
la verificación en dos pasos tiene su propio límite, por usuario
([HU-37](#login-con-verificación-en-dos-pasos-post-auth2faverify--hu-37)).

### Login social (`POST /auth/social/{provider}`) · HU-38

Público. El frontend redirige al proveedor, recibe `?code` en su página de callback y lo envía:
`{"code": str, "redirect_uri": str}`. `redirect_uri` debe ser de un origen de `ALLOWED_ORIGINS`.
Devuelve `{"access_token", "token_type"}`, igual que `/auth/login`.

- Cuenta social ya vinculada → inicia sesión.
- Si no, hace falta un email **verificado** por el proveedor (Google: `email_verified`; GitHub:
  el email primario verificado). Si ya existe un usuario con ese email se vincula (conserva su
  rol); si no, se crea un `customer` sin contraseña. En los dos casos queda
  `email_verified=true` (HU-33, R-15).
- Un usuario inactivo o borrado no entra. Un usuario sin contraseña no puede usar `/auth/login`.
- Variables: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`.

| HTTP | `code` | Cuándo |
|---|---|---|
| 401 | `invalid_code` | `code` inválido o caducado |
| 401 | `email_not_verified` | El proveedor no da un email verificado |
| 401 | `inactive_account` | Usuario inactivo o borrado |
| 422 | `redirect_uri_not_allowed` | `redirect_uri` fuera de los orígenes permitidos (un `provider` desconocido → `validation_error`) |
| 502 | `provider_unavailable` | Google o GitHub no responden |
| 503 | `provider_not_configured` | Faltan el client id o el secreto del proveedor |

### Login con verificación en dos pasos (`POST /auth/2fa/verify`) · HU-37

Si el usuario tiene la 2FA activada, `POST /auth/login` y `POST /auth/social/{provider}` no
devuelven el JWT sino `{"mfa_required": true, "mfa_token": "..."}` (`200`). El `mfa_token`
caduca en 5 min y no sirve como access token. El cliente pide el código y lo canjea:

```json
{"mfa_token": "eyJhbGciOiJIUzI1NiIs...", "code": "123456"}
```

`code` es el código de 6 dígitos de la app de autenticación (se acepta ±30 s) o un código de
recuperación (`a1b2c3d4e5-f6a7b8c9d0`, de un solo uso). Respuesta `200`: `{"access_token", "token_type"}`.

Límite de intentos (HU-31, R-10): tras 5 códigos incorrectos (`invalid_totp_code`) de la misma
cuenta en 15 minutos, responde `429` `too_many_attempts` con `Retry-After`, también con un
código correcto y desde cualquier IP. Cuenta por usuario, no por IP: para llegar aquí hace
falta la contraseña. Un código correcto borra los fallos.

| HTTP | `code` | Cuándo |
|---|---|---|
| 401 | `invalid_mfa_token` | `mfa_token` no válido o caducado, o usuario inactivo, borrado o sin 2FA |
| 401 | `invalid_totp_code` | Código incorrecto o código de recuperación ya usado |

### Usuario autenticado (`GET /auth/me`)

Requiere `Authorization: Bearer <token>` y devuelve el `UserOut` del token. Sin token o
con un token no válido o caducado → `401`.

### Códigos de error

| HTTP | `code` | Cuándo |
|---|---|---|
| 401 | `unauthorized` | Credenciales incorrectas, usuario inactivo, o token ausente/no válido |
| 409 | `conflict` | El email ya está registrado (R-01) |
| 422 | `validation_error` | Email con formato incorrecto, contraseña < 8 caracteres o campos que faltan (R-02) |
| 429 | `too_many_attempts` | `POST /auth/login`: demasiados intentos fallidos desde esa IP para ese email (R-10); ver `Retry-After` |

## Mesas disponibles (`GET /tables/available`) · HU-18

Roles: `admin` y `waiter`. `kitchen` y `customer` → `403`.

Devuelve las mesas libres para un hueco, en el formato paginado común
(`{"items": [DiningTableRead], "total", "page", "size"}`).

| Parámetro | Obligatorio | Descripción |
|---|---|---|
| `reserved_at` | Sí | Inicio del hueco (`2026-10-10T21:00:00`). Si llega con zona horaria se convierte a UTC, igual que en las reservas |
| `party_size` | Sí | Número de personas (> 0) |
| `duration_min` | No | Duración del hueco en minutos (1..480, por defecto 90) |
| `page`, `size` | No | Paginación (por defecto 1 y 20) |

Una mesa está disponible si:

- `capacity >= party_size`;
- su `status` no es `out_of_service`;
- no tiene ninguna reserva activa (`status != cancelled`) que se solape con
  `[reserved_at, reserved_at + duration_min)`. Es la misma regla de solapamiento que usa
  `POST /reservations`, así que una mesa devuelta aquí se puede reservar en ese hueco.

Se ordenan por `capacity` y `number`: la mesa que mejor se ajusta al grupo sale primero.
Si no hay ninguna libre la respuesta es `200` con `items: []`. Parámetros que faltan o no
son válidos → `422`.

```http
GET /tables/available?reserved_at=2026-10-10T21:00:00&party_size=4
```

```json
{
  "items": [
    {"id": 3, "number": 12, "capacity": 4, "location": "terrace", "status": "available"}
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

## Reservas (`/reservations`) · HU-10, HU-19, HU-51

Roles: `admin` y `waiter` operan sobre todas las reservas; `customer` solo sobre las suyas
(`403` si intenta tocar una ajena); `kitchen` no tiene acceso (`403`).

| Método | Ruta | Qué hace | Éxito |
|---|---|---|---|
| `POST` | `/reservations` | Crear una reserva (`confirmed`) y enviar el email en segundo plano | `201` |
| `GET` | `/reservations` | Listar con filtros `?status&table_id&date&user_id&page&size` | `200` |
| `GET` | `/reservations/{id}` | Ver el detalle | `200` |
| `PATCH` | `/reservations/{id}` | Edición parcial | `200` |
| `PATCH` | `/reservations/{id}/cancel` | Cancelar y enviar el email en segundo plano | `200` |
| `DELETE` | `/reservations/{id}` | Borrar definitivamente | `204` |

### Reglas de negocio

- **Solapamiento:** dos reservas activas (`status != cancelled`) de la misma mesa no pueden
  solaparse. Los intervalos son semiabiertos, `[reserved_at, reserved_at + duration_min)`:
  una reserva que acaba a las 21:30 no choca con otra que empieza a las 21:30.
  Si se solapan → `409` con `code="reservation_conflict"`.
- **Aforo:** `party_size` no puede superar `dining_tables.capacity` → `422` con
  `code="party_size_exceeds_capacity"`.
- **Asignación automática (HU-51):** `table_id` es opcional. Sin él, el backend elige la
  mesa libre más pequeña con sitio para `party_size` en ese hueco (la primera de
  `GET /tables/available`) y la devuelve en `table_id`. Vale para todos los roles. Si no hay
  ninguna → `409` con `code="no_table_available"` y el mensaje
  "No hay mesa libre para N personas el DD/MM/AAAA a las HH:MM". Sin `table_id`, una
  `reserved_at` en el pasado (respecto a la hora local del restaurante, variable
  `RESTAURANT_TIMEZONE`, por defecto `Europe/Madrid`) → `422` con
  `code="reservation_in_past"`; con `table_id` no se
  valida, como antes.
- **Máximo de 8 personas para el cliente (HU-51):** un `customer` que crea o edita una reserva
  con `party_size` mayor que 8 → `422` con `code="party_size_too_large"` y el mensaje
  "Para reservas de más de 8 personas, llama al restaurante". `admin` y `waiter` no tienen
  este límite.
- **Cancelar libera el hueco:** una reserva cancelada deja de contar para el solapamiento.
- `reserved_at` se guarda **sin zona horaria**. Si se envía con zona
  (`2026-10-10T22:00:00+02:00`), se convierte a UTC (`2026-10-10T20:00:00`).
- `duration_min`: por defecto 90, entre 1 y 480.

### Crear (`POST /reservations`)

```json
{
  "table_id": 3,
  "reserved_at": "2026-10-10T21:00:00",
  "duration_min": 90,
  "party_size": 4,
  "notes": "Cumpleaños, trona para un bebé"
}
```

Un `customer` normalmente no envía `table_id`:

```json
{
  "reserved_at": "2026-10-10T21:00:00",
  "party_size": 4,
  "notes": "Cumpleaños, trona para un bebé"
}
```

`user_id` es opcional y solo lo pueden indicar `admin` y `waiter` (reservas por teléfono).
Si se omite, la reserva es del usuario autenticado. Si un `customer` lo envía con otro id → `403`.

Respuesta `201` (también la de `GET`, `PATCH` y `/cancel`):

```json
{
  "id": 1,
  "user_id": 7,
  "table_id": 3,
  "reserved_at": "2026-10-10T21:00:00",
  "duration_min": 90,
  "ends_at": "2026-10-10T22:30:00",
  "party_size": 4,
  "status": "confirmed",
  "notes": "Cumpleaños, trona para un bebé",
  "created_at": "2026-10-06T10:15:00"
}
```

`ends_at` es un campo calculado (`reserved_at + duration_min`) y solo existe en la respuesta.

### Editar (`PATCH /reservations/{id}`)

Se cambian solo los campos enviados: `table_id`, `reserved_at`, `duration_min`, `party_size`,
`notes` y `status`. Un `customer` no puede subir `party_size` por encima de 8. No se reasigna la mesa sola. Si cambia la mesa, la hora, la duración o las personas, se revalidan el aforo
y el solapamiento. `status` solo lo pueden cambiar `admin` y `waiter`, y solo a `confirmed`,
`completed` o `no_show`. Para cancelar se usa `/cancel`, que es el que envía el email.

### Cancelar (`PATCH /reservations/{id}/cancel`)

Solo se pueden cancelar reservas `confirmed`. Si no lo está → `409` con
`code="reservation_not_cancellable"`. El email de cancelación se envía con `BackgroundTasks`,
así que no retrasa la respuesta. Con `EMAIL_ENABLED=false` solo se escribe en el log.

### Emails de reserva (HU-19)

- **Confirmación:** al crear una reserva (`POST /reservations`) se envía un email al usuario
  dueño de la reserva con la fecha, la hora, la mesa y el nº de personas.
- **Cancelación:** al cancelarla (`PATCH /reservations/{id}/cancel`) se envía otro con los
  mismos datos.
- Se envían en segundo plano con `BackgroundTasks`: la respuesta (`201` / `200`) no espera
  al email.
- El envío usa la API de Brevo (`POST https://api.brevo.com/v3/smtp/email`) con
  `BREVO_API_KEY` y el remitente `MAIL_FROM`.
- Con `EMAIL_ENABLED=false` (local y CI) no se envía nada: solo se registra en el log.
- Si Brevo falla (error HTTP, timeout, credenciales que faltan), la reserva se guarda igual y
  el error queda en el log. El endpoint nunca devuelve un error por culpa del email.

### Códigos de error

| HTTP | `code` | Cuándo |
|---|---|---|
| 403 | `reservation_forbidden` | Un customer crea, filtra o edita el estado de una reserva ajena |
| 403 | `forbidden` | Rol sin permiso, o un customer accede a una reserva ajena (`ensure_owner_or_role`) |
| 404 | `reservation_not_found` | La reserva no existe |
| 404 | `table_not_found` | La mesa no existe |
| 404 | `user_not_found` | El `user_id` indicado por admin o waiter no existe |
| 409 | `reservation_conflict` | Solapamiento con otra reserva activa de la mesa |
| 409 | `reservation_not_cancellable` | Se intenta cancelar una reserva que no está `confirmed` |
| 422 | `party_size_exceeds_capacity` | `party_size` supera la capacidad de la mesa |
| 422 | `validation_error` | Validación de Pydantic (campos que faltan, `party_size <= 0`, campos desconocidos…) |

## Usuarios (`/users`) · HU-32, HU-24

Todos los endpoints son solo `admin` (otro rol → `403`), salvo los del propio perfil
(`PATCH /users/me` y `POST /users/me/password`), abiertos a cualquier rol autenticado: ver
[Perfil propio](#perfil-propio-usersme--hu-25).

| Endpoint | Descripción |
|---|---|
| `POST /users/` | Crea un usuario; guarda `created_by` y `updated_by` (el admin que lo crea) |
| `GET /users/` | Lista paginada (`Page[UserOut]`) de los usuarios no borrados. `?include_deleted=true` incluye los borrados. Filtros y búsqueda: ver abajo (HU-24) |
| `GET /users/{id}` | Un borrado → `404`, salvo con `?include_deleted=true` |
| `PUT /users/{id}` | Edita; actualiza `updated_by` y `updated_at` |
| `PATCH /users/{id}/deactivate` | `is_active=false`: suspensión temporal, sigue en los listados y no puede iniciar sesión |
| `DELETE /users/{id}` | Soft delete: `deleted_at` + `is_active=false`; desaparece de los listados. Devuelve el usuario |
| `POST /users/{id}/restore` | `deleted_at=null` e `is_active=true`. Solo si estaba borrado |

`UserOut` incluye `updated_at`, `deleted_at`, `created_by` y `updated_by` (nulos en usuarios anteriores a la HU-32 o creados por auto-registro), y `email_verified` (HU-33; los creados con `POST /users/` nacen con `true`). Un usuario nunca se borra físicamente; su email sigue reservado (crearlo otra vez → `409`).

| Código | Cuándo |
|---|---|
| `403` | Un admin intenta borrarse o desactivarse a sí mismo |
| `404` | Usuario inexistente o ya borrado |
| `409` | Email ya registrado; `restore` sobre un usuario no borrado |

### Filtrar, buscar y paginar (`GET /users/`) · HU-24

**Breaking-api**: la respuesta pasa de una lista a `{"items", "total", "page", "size"}` y se quitan `skip`/`limit`.

| Parámetro | Tipo | Efecto |
|---|---|---|
| `page` | int ≥ 1 (por defecto 1) | Página |
| `size` | int 1-100 (por defecto 20) | Elementos por página |
| `role` | `admin`, `waiter`, `kitchen`, `bartender`, `customer` | Solo ese rol. Otro valor → `422` |
| `is_active` | bool | `true` solo activos, `false` solo desactivados. Sin valor: todos |
| `q` | texto, máx. 100 caracteres (más → `422`) | Búsqueda parcial, sin distinguir mayúsculas ni acentos (`jose` encuentra "José"), en `name` o `email`. Vacío o solo espacios: no filtra. `%` y `_` cuentan como texto |
| `include_deleted` | bool (por defecto `false`) | Incluye los borrados (HU-32) |

Los parámetros se combinan entre sí; `total` cuenta los usuarios que cumplen todos los filtros. Orden fijo por `id` ascendente. Ejemplo: `GET /users/?role=waiter&q=ana&page=1&size=20`.

## Perfil propio (`/users/me`) · HU-25

Cualquier rol autenticado (`admin`, `waiter`, `kitchen`, `bartender`, `customer`) sobre sus
propios datos. Requiere `Authorization: Bearer <token>`; sin token o con un token no
válido → `401`. Para ver los datos se usa `GET /auth/me`.

| Método | Ruta | Qué hace | Éxito |
|---|---|---|---|
| `PATCH` | `/users/me` | Edita el `name`, el `email` y el `phone` propios | `200` |
| `POST` | `/users/me/password` | Cambia la propia contraseña indicando la actual | `204` |
| `GET` | `/users/me/2fa` | Estado de la verificación en dos pasos (HU-37) | `200` |
| `POST` | `/users/me/2fa/setup` | Prepara la 2FA: secreto nuevo y QR | `200` |
| `POST` | `/users/me/2fa/enable` | Activa la 2FA con un primer código | `200` |
| `POST` | `/users/me/2fa/disable` | Desactiva la 2FA con un código | `200` |

### Editar mi perfil (`PATCH /users/me`)

Edición parcial: solo se aplican los campos enviados.

```json
{"name": "Ana López", "email": "Ana@Example.com", "phone": "600123456"}
```

- **Campos editables:** `name` (1..100 caracteres), `email` y `phone` (máx. 20 caracteres).
  `{"phone": null}` borra el teléfono; `name` y `email` no admiten `null` (`422`).
- **Nada más se puede cambiar:** cualquier otro campo (`role`, `is_active`, `password`…) →
  `422` `validation_error`. El rol y la activación siguen siendo cosa de un admin (R-03, R-04).
- **Email** guardado en minúsculas y único sin distinguir mayúsculas (R-01). Si ya es de
  otro usuario, incluidos los borrados → `409`. Enviar el mismo email que ya tienes es válido.
- **Cambiar el email pide verificarlo de nuevo** (HU-33, R-15): `email_verified=false`, se
  invalidan los enlaces de verificación pendientes y se envía uno nuevo a la dirección
  nueva, sin tiempo de espera. La respuesta sigue siendo `200` y no se pierde el acceso.
  Con el mismo email o sin `email` en el cuerpo, `email_verified` no cambia.
- Guarda `updated_by` con el propio id (R-11) y actualiza `updated_at`.

Respuesta `200` (`UserOut`; nunca incluye `password_hash`):

```json
{"id": 7, "name": "Ana López", "email": "ana@example.com", "phone": "600123456",
 "role": "customer", "is_active": true, "email_verified": false,
 "created_at": "2026-10-14T10:15:00", "updated_at": "2026-10-15T09:30:00",
 "deleted_at": null, "created_by": null, "updated_by": 7}
```

### Cambiar mi contraseña (`POST /users/me/password`)

```json
{"current_password": "OldPassw0rd", "new_password": "NewPassw0rd"}
```

Respuesta `204` sin cuerpo. La nueva contraseña debe tener al menos 8 caracteres (R-02) y
se guarda hasheada con bcrypt; nunca se devuelve ni se escribe en el log. A partir de ese
momento `POST /auth/login` funciona con la nueva y deja de funcionar con la anterior.

> **Nota:** cambiar la contraseña no cierra las otras sesiones abiertas: los tokens ya
> emitidos siguen siendo válidos hasta que caducan. Invalidarlos queda para la HU de
> refresh/logout (R-06/R-07).

### Códigos de error

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `password_not_set` | La cuenta no tiene contraseña (solo login social): `"Password not set for this account"` |
| 401 | `unauthorized` | Sin token o token no válido o caducado |
| 403 | `invalid_current_password` | `current_password` no es la contraseña actual: `"Current password is incorrect"` |
| 409 | `conflict` | `PATCH /users/me`: el email ya pertenece a otro usuario: `"Email already registered"` (R-01) |
| 422 | `validation_error` | Campos no editables o desconocidos (`role`, `is_active`…), `name` vacío, `null` en `name`/`email`, email con formato incorrecto o `new_password` < 8 caracteres |
| 422 | `same_password` | `new_password` es igual a la actual: `"New password must be different from the current one"` |

### Verificación en dos pasos (`/users/me/2fa`) · HU-37

1. `POST /users/me/2fa/setup` → `{"secret", "otpauth_uri", "qr_svg"}`. Se escanea el QR (o se
   teclea `secret`) en una app de autenticación. El secreto se guarda cifrado y aún no está activo.
2. `POST /users/me/2fa/enable` `{"code": "123456"}` → `{"recovery_codes": [...]}`: 8 códigos de
   un solo uso que solo se muestran esta vez (se guardan con hash).
3. `GET /users/me/2fa` → `{"enabled": true, "recovery_codes_left": 8}`.
4. `POST /users/me/2fa/disable` `{"code": "..."}` (TOTP o código de recuperación) →
   `{"enabled": false, "recovery_codes_left": 0}`; borra el secreto y los códigos.

Ninguna respuesta de la API devuelve el secreto salvo `setup`, y nunca se escribe en el log.

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `invalid_totp_code` | `enable` o `disable` con un código incorrecto |
| 409 | `totp_already_enabled` | `setup` o `enable` con la 2FA ya activada |
| 409 | `totp_not_set_up` | `enable` sin `setup` previo |
| 409 | `totp_not_enabled` | `disable` sin la 2FA activada |

## Invitación y crear la contraseña · HU-52

El admin da de alta a un usuario **sin contraseña** y este la crea con el enlace que le
llega por email. El enlace lleva un `PasswordResetToken` de un solo uso que caduca a las
`PASSWORD_TOKEN_EXPIRE_HOURS` horas (48 por defecto) (R-09). Solo se guarda el SHA-256 del
token, y el token nunca aparece en el log.

| Endpoint | Rol | Respuesta |
|---|---|---|
| `POST /users/invite` | `admin` | `201` con `UserOut`. Envía el email en segundo plano |
| `POST /auth/set-password` | Público | `204` sin cuerpo |

### Invitar (`POST /users/invite`)

```json
{"name": "Lucía Gómez", "email": "lucia@example.com", "phone": "600123456", "role": "customer"}
```

`phone` es opcional y `role` vale `customer` por defecto. El usuario se crea con
`password_hash` nulo, así que no puede iniciar sesión hasta crear su contraseña, y con
`email_verified=false` (HU-33). El email
("Crea tu contraseña de APIResto") lleva el enlace
`{FRONTEND_URL}/crear-contrasena?token=…`; con `EMAIL_ENABLED=false` solo se registra en
el log, sin el enlace.

### Crear la contraseña (`POST /auth/set-password`)

```json
{"token": "token-del-enlace-del-email", "new_password": "MiClave2026"}
```

Guarda la contraseña (bcrypt, mínimo 8 caracteres, R-02) y marca como usados todos los
tokens pendientes del usuario. Después se entra con `POST /auth/login`.

Sirve también para la recuperación de HU-33 (el token de `POST /auth/forgot-password`). Con
cualquiera de los dos tokens marca además `email_verified=true`, porque el enlace llegó por
email (R-15). La respuesta sigue siendo `204`.

### Códigos de error

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `invalid_token` | Token desconocido, o usuario desactivado o borrado: `"Invalid token"` |
| 401 | `unauthorized` | `POST /users/invite` sin token o con token no válido |
| 403 | `forbidden` | `POST /users/invite` con un rol que no es `admin` |
| 409 | `conflict` | `POST /users/invite`: el email ya está registrado (R-01) |
| 410 | `token_used` | El token ya se usó: `"Token already used"` |
| 410 | `token_expired` | El token ha caducado: `"Token expired"` |
| 422 | `validation_error` | Email con formato incorrecto, campos desconocidos o `new_password` < 8 caracteres |

## Verificación de email y recuperación de contraseña · HU-33

La verificación es **informativa** (R-15): `email_verified` sale en `UserOut` y
`POST /auth/login` no la comprueba. Ningún endpoint existente cambia su código de respuesta
ni sus errores; `UserOut` solo gana el campo `email_verified` (aditivo, sin breaking-api).

| Endpoint | Rol | Respuesta |
|---|---|---|
| `POST /auth/verify-email` | Público | `204` sin cuerpo |
| `POST /auth/resend-verification` | Público | `202` |
| `POST /auth/forgot-password` | Público | `202` |

**Quién nace verificado** (`email_verified`):

| Origen de la cuenta | `email_verified` |
|---|---|
| `POST /auth/register` | `false`; se envía el email de verificación |
| `POST /users/` (admin) | `true` |
| `POST /users/invite` | `false`; pasa a `true` con `POST /auth/set-password` |
| Login social, cuenta nueva o vinculada | `true` |
| `python -m app.scripts.create_admin` (también al promover una cuenta) | `true` |
| Cuentas anteriores a la migración `0009` | `true` |

Los enlaces llevan un token de un solo uso (R-09): solo se guarda su SHA-256 y nunca
aparece en el log ni en una respuesta. Los emails se envían en segundo plano; con
`EMAIL_ENABLED=false` solo se registra el envío, sin el enlace.

| Email | Asunto | Enlace | Caduca |
|---|---|---|---|
| Verificación | "Verifica tu email de APIResto" | `{FRONTEND_URL}/verificar-email?token=…` | `EMAIL_VERIFY_EXPIRE_HOURS` (48 h) |
| Recuperación | "Restablece tu contraseña de APIResto" | `{FRONTEND_URL}/restablecer-contrasena?token=…` | `PASSWORD_RESET_EXPIRE_HOURS` (1 h) |

### Verificar el email (`POST /auth/verify-email`)

```json
{"token": "token-del-enlace-del-email"}
```

Lo llama la página `/verificar-email` del frontend. Marca `email_verified=true` y marca como
usados ese token y los demás enlaces de verificación pendientes del usuario. Si la cuenta
ya estaba verificada y el token es válido, responde `204` igualmente y lo consume.

### Reenviar la verificación (`POST /auth/resend-verification`)

```json
{"email": "ana@example.com"}
```

Envía otro enlace si la cuenta no está verificada. No requiere token: sirve también a
quien aún no ha iniciado sesión.

### Olvidé mi contraseña (`POST /auth/forgot-password`)

```json
{"email": "ana@example.com"}
```

Envía un enlace con un `PasswordResetToken` que caduca a las `PASSWORD_RESET_EXPIRE_HOURS`
horas (1 por defecto; la invitación de HU-52 sigue con `PASSWORD_TOKEN_EXPIRE_HOURS`). La
contraseña nueva se fija con [`POST /auth/set-password`](#crear-la-contraseña-post-authset-password),
sin cambios en su contrato. También llega a cuentas sin contraseña (solo login social o
invitadas), que así pueden crear una.

### Respuesta `202` idéntica y tiempo de espera

`resend-verification` y `forgot-password` responden **siempre** `202` con el mismo cuerpo,
exista o no la cuenta, para no revelar qué emails están registrados:

```json
{"detail": "If the account exists, an email has been sent"}
```

El email se compara en minúsculas (R-01). Solo se envía si la cuenta existe, está activa y
no está borrada (R-04), y no está en el tiempo de espera; `resend-verification` exige además
que no esté verificada. En cualquier otro caso no se envía nada y solo queda un log, sin
el email.

**Tiempo de espera:** no se emite otro token del mismo tipo si el último del usuario se
creó hace menos de `TOKEN_RESEND_COOLDOWN_SECONDS` (60 por defecto). Es silencioso: no
devuelve `429`, porque un `429` solo aparecería con emails registrados. El enlace de
`POST /auth/register` cuenta como último envío; el de `PATCH /users/me` no espera.

### Códigos de error

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `invalid_token` | `verify-email`: token desconocido, o usuario desactivado o borrado: `"Invalid token"` |
| 410 | `token_used` | `verify-email`: el token ya se usó: `"Token already used"` |
| 410 | `token_expired` | `verify-email`: el token ha caducado: `"Token expired"` |
| 422 | `validation_error` | Falta `token` o `email`, email con formato incorrecto o campos de más |

## Pedidos (`/orders`) · HU-07, HU-05, HU-45

| Endpoint | Roles |
|---|---|
| `POST /orders/` | `admin`, `waiter`. El pedido guarda en `waiter_id` el usuario que lo crea |
| `GET /orders/`, `GET /orders/{id}` | `admin`, `waiter`, `kitchen`, `bartender`. Cada línea trae `station` (`kitchen` / `bar`, la de la categoría de su plato). `kitchen` y `bartender` solo reciben las líneas de su estación y no ven los pedidos que no tienen ninguna (`404` en `GET /orders/{id}`); `total` es el del pedido completo (R-14) |
| `PATCH /orders/{id}/status` | `admin`, `waiter`, `kitchen`, `bartender`. `kitchen` y `bartender` solo sobre pedidos con líneas de su estación (si no, `404`); la respuesta trae solo esas líneas |
| `PATCH /orders/{id}/items/{item_id}` | Marca cuántas unidades de una línea están preparadas o servidas: `{"prepared_quantity": 1}` (de 0 a `quantity`; si es mayor, 422). `{"prepared": true}` marca todas y `false`, ninguna. `prepared` / `prepared_quantity`: `admin`, `kitchen`, `bartender`. `served` / `served_quantity`: `admin`, `waiter`. `kitchen` y `bartender` solo sobre líneas de su estación; otra estación → `403`. La respuesta trae `prepared_quantity`, `served_quantity` y `prepared` / `served` (true si están todas) |

Sin token → `401`. `customer` en cualquier endpoint, `kitchen` o `bartender` creando un pedido o marcando `served`, o `waiter` marcando `prepared` → `403`.

Cada línea de `items` lleva `prepared` (cocina o barra la tiene lista) y `served` (sala la ha llevado a la mesa), las dos `false` al crear el pedido. Marcar una línea de otro pedido o que no existe → `404`; de un pedido `paid` o `cancelled` → `409`; sin `prepared` ni `served` en el cuerpo → `422`.

El WebSocket de cocina (`/ws/kitchen`) admite `admin`, `kitchen` y `bartender`. Cada evento (`order_created`, `order_status_changed`) trae `order.stations` y, en `order_created`, `items` con su `station`; `kitchen` y `bartender` solo reciben los pedidos con líneas de su estación y con esas líneas, `admin` recibe todo.

### Progreso del pedido (`progress`) · HU-45

Todas las respuestas de pedidos (`POST /orders/`, `GET /orders/`, `GET /orders/{id}` y los dos `PATCH`) traen el progreso del pedido. Se calcula al responder a partir de las unidades preparadas y servidas de cada línea: no hay campos nuevos en la base de datos ni migración, y no cambia el `status` del pedido (R-16).

- Cada línea trae `ready_to_serve`: unidades preparadas que aún no se han servido (`prepared_quantity - served_quantity`, nunca menos de 0).
- `progress` suma las líneas de la respuesta: `quantity`, `prepared_quantity`, `served_quantity`, `ready_to_serve` (la suma de las líneas, no la resta de los totales) y `stage`.
- `progress.by_station` repite el cálculo para `kitchen` y `bar`, con su propio `stage`. Solo aparecen las estaciones que tiene el pedido.
- `admin` y `waiter` ven el total y las dos estaciones. `kitchen` y `bartender` solo reciben sus líneas (R-14), así que ven su progreso y una sola entrada en `by_station`.

| `stage` | Cuándo |
| --- | --- |
| `all_served` | Todas las unidades están servidas (un pedido sin líneas queda `waiting`) |
| `ready_to_serve` | Hay unidades preparadas sin servir: sala tiene algo que llevar a la mesa |
| `waiting` | No hay nada preparado ni servido |
| `preparing` | Cualquier otro caso: algo hecho y nada pendiente de llevar |

Ejemplo: 2 pastas (1 preparada y servida) y 2 cervezas (las 2 preparadas, ninguna servida), visto por `waiter`:

```json
{
  "items": [
    {"dish_id": 1, "quantity": 2, "prepared_quantity": 1, "served_quantity": 1, "station": "kitchen", "ready_to_serve": 0},
    {"dish_id": 2, "quantity": 2, "prepared_quantity": 2, "served_quantity": 0, "station": "bar", "ready_to_serve": 2}
  ],
  "progress": {
    "quantity": 4,
    "prepared_quantity": 3,
    "served_quantity": 1,
    "ready_to_serve": 2,
    "stage": "ready_to_serve",
    "by_station": {
      "kitchen": {"quantity": 2, "prepared_quantity": 1, "served_quantity": 1, "ready_to_serve": 0, "stage": "preparing"},
      "bar": {"quantity": 2, "prepared_quantity": 2, "served_quantity": 0, "ready_to_serve": 2, "stage": "ready_to_serve"}
    }
  }
}
```

El mismo pedido visto por `kitchen` trae solo la línea de pasta, y `progress` y `by_station.kitchen` valen `{"quantity": 2, "prepared_quantity": 1, "served_quantity": 1, "ready_to_serve": 0, "stage": "preparing"}`. Se puede marcar como servida una unidad que no se ha preparado: no da error y `ready_to_serve` se queda en 0.

## Facturas y exportación CSV · HU-14

Una factura por pedido, solo para pedidos `served`. Facturar **no** cambia el estado del
pedido (sigue `served`; después se marca `paid` con `PATCH /orders/{id}/status`).

- **IVA:** 10 %, incluido en el precio de los platos. `base_amount = total / 1,10`
  (redondeado a céntimos) y `tax_amount = total - base_amount`, así que
  `base_amount + tax_amount = total` siempre.
- **Número:** `F-AÑO-NNNNN` (`F-2026-00001`). El correlativo vuelve a `00001` cada año.

| Método | Ruta | Roles | Descripción |
|---|---|---|---|
| POST | `/orders/{order_id}/invoice` | admin, waiter | Genera la factura del pedido → `201` |
| GET | `/invoices` | admin, waiter | Listado paginado (`Page[InvoiceOut]`) ordenado por número. Filtros `date_from`, `date_to` (fecha de emisión, ambos incluidos) |
| GET | `/invoices/{invoice_id}` | admin, waiter | Una factura |
| GET | `/exports/invoices` | admin | CSV de facturas. Filtros `date_from`, `date_to` |
| GET | `/exports/orders` | admin | CSV de pedidos. Filtros `status`, `date_from`, `date_to` (fecha de creación) |

Factura (`InvoiceOut`):

```json
{"id": 1, "number": "F-2026-00001", "order_id": 7, "base_amount": "20.00",
 "tax_rate": "0.10", "tax_amount": "2.00", "total": "22.00",
 "issued_at": "2026-10-08T12:52:48"}
```

### CSV

Se descargan como archivo: `Content-Type: text/csv` y
`Content-Disposition: attachment; filename="invoices.csv"`. Si hay filtro de fechas, el
nombre las incluye (`orders_2026-01-01_2026-01-31.csv`). Separador `,`, decimales con
punto, fechas ISO 8601 y UTF-8 con BOM (para que Excel lea bien los acentos).

- `invoices.csv`: `number, issued_at, order_id, table_id, base_amount, tax_rate, tax_amount, total`
- `orders.csv`: `id, created_at, table_id, waiter_id, status, items, total, invoice_number`
  (`items` = suma de cantidades; `invoice_number` vacío si no tiene factura)

### Códigos de error

| HTTP | `code` | Cuándo |
|---|---|---|
| 404 | `not_found` | El pedido o la factura no existen |
| 409 | `order_not_served` | Se intenta facturar un pedido que no está `served` |
| 409 | `invoice_already_exists` | El pedido ya tiene factura |
| 409 | `invoice_conflict` | Dos facturas a la vez chocan con el mismo número; reintentar |
| 422 | `invalid_date_range` | `date_from` es posterior a `date_to` |
| 422 | `validation_error` | Fecha con formato incorrecto o `status` no válido |

## Estadísticas (`/stats`) · HU-15

Solo `admin`. Otro rol → `403`; sin token → `401`.

- **Qué cuenta como venta:** los pedidos `served` y `paid`. Los `pending` e `in_kitchen`
  todavía no son venta y los `cancelled` no lo son nunca.
- **Fechas:** `from` y `to` (`YYYY-MM-DD`) son opcionales, filtran por la fecha de creación
  del pedido y las dos están incluidas. Sin fechas, se usan todos los pedidos.
- **Importes:** texto con 2 decimales, como en las facturas.
- **Caché:** cada respuesta se guarda en memoria `STATS_CACHE_TTL` segundos (60 por
  defecto; `0` = sin caché), una entrada por combinación de parámetros. Durante ese tiempo
  los pedidos nuevos no aparecen.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/stats/sales` | Número de pedidos, total vendido, ticket medio y desglose por día. Filtros `from`, `to` |
| GET | `/stats/top-dishes` | Platos más vendidos por unidades, con sus ingresos. Filtros `from`, `to` y `limit` (por defecto 5, de 1 a 50) |

Ventas (`GET /stats/sales?from=2026-10-01&to=2026-10-02`):

```json
{"date_from": "2026-10-01", "date_to": "2026-10-02", "orders_count": 3,
 "total_sales": "42.50", "average_ticket": "14.17",
 "daily": [{"day": "2026-10-01", "orders_count": 2, "total_sales": "38.50"},
           {"day": "2026-10-02", "orders_count": 1, "total_sales": "4.00"}]}
```

- `average_ticket = total_sales / orders_count`, redondeado a céntimos (`0.00` si no hay
  pedidos).
- `daily` solo incluye los días con ventas, ordenados por fecha.

Platos más vendidos (`GET /stats/top-dishes?limit=2`):

```json
[{"dish_id": 3, "name": "Croquetas", "quantity": 5, "revenue": "32.50"},
 {"dish_id": 5, "name": "Flan", "quantity": 4, "revenue": "16.00"}]
```

- `revenue = quantity × unit_price` de cada línea del pedido, es decir, con el precio que
  tenía el plato al pedirlo, no con el precio actual de la carta.
- Orden: más unidades primero; si hay empate, más ingresos y después menor `dish_id`.
- Lista vacía si no hay ventas en el periodo.

### Códigos de error

| HTTP | `code` | Cuándo |
|---|---|---|
| 401 | `unauthorized` | Sin token o token no válido |
| 403 | `forbidden` | El usuario no es `admin` |
| 422 | `invalid_date_range` | `from` es posterior a `to` |
| 422 | `validation_error` | Fecha con formato incorrecto o `limit` fuera de 1..50 |