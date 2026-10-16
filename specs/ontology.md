# Ontología del dominio — Identidad y acceso

> Vocabulario compartido entre el equipo y los agentes. Prosa en español,
> identificadores en inglés. Prioridad: **M** Must · **S** Should · **C** Could.
> Aprobada por Levi (PO). Las issues, los PR y el ai-log citan las reglas por su id (R-xx).

## 1. Glosario (EN ↔ ES)

| Identificador | Término de negocio | Significado |
|---|---|---|
| `User` | usuario | Persona con cuenta en RestoAPI |
| `Role` | rol | Perfil de permisos: `admin`, `waiter`, `kitchen`, `bartender`, `customer` |
| `bartender` | barra | Rol de la estación de barra (bebidas/postres); no se llama `bar` para no chocar con la ubicación de mesa |
| `customer` | cliente | Rol por defecto del auto-registro (equivale al `user` del brief P3) |
| `AccessToken` | token de acceso | JWT corto que autoriza peticiones |
| `RefreshToken` | token de renovación | Credencial larga, de un solo uso, para obtener un nuevo par |
| `RevokedToken` | token revocado | `jti` de un access token invalidado antes de caducar |
| `EmailVerificationToken` | token de verificación | Un solo uso, confirma que el email es del usuario |
| `PasswordResetToken` | token de recuperación | Un solo uso, permite fijar una contraseña nueva |
| `SocialAccount` | cuenta social | Vínculo de un usuario con Google/GitHub |
| `jti` | identificador de token | Id único dentro del JWT |
| `Station` | estación | Valor (`kitchen` / `bar`) de `Category.station` que decide a qué rol llega cada línea de un pedido (R-14); no es una entidad |
| `OrderProgress` | progreso del pedido | Resumen calculado de las unidades preparadas, servidas y listas para servir de un pedido, total y por estación (R-16); no es una entidad |

## 2. Entidades

### User (M) — tabla `users`
| Atributo | Tipo | Reglas |
|---|---|---|
| `id` | int, PK | |
| `name` | str | obligatorio |
| `email` | str | único, minúsculas (R-01) |
| `password_hash` | str | bcrypt; nunca expuesto (R-02) |
| `phone` | str, opcional | |
| `role` | str(20), valor del enum `Role` | obligatorio, por defecto `customer` (R-03) |
| `is_active` | bool | por defecto `true`; "borrar" = `false` (R-04) |
| `created_at`, `updated_at` | datetime UTC | `updated_at` nuevo en P3 |
| `email_verified` | bool | (S) por defecto `false`; informativo, no bloquea el login (R-15) |
| `deleted_at`, `created_by`, `updated_by` | datetime / FK users, nulos | (S) soft delete + auditoría |
| `totp_secret`, `totp_enabled` | str cifrado / bool | (C) 2FA |
| `totp_recovery_codes` | str, nulo | (C) 2FA: SHA-256 de los códigos de recuperación sin usar, separados por comas (HU-37) |

### Role (M) — enum `Role`, sin tabla
Valores: `admin`, `waiter`, `kitchen`, `bartender`, `customer`. Se guarda como string en `users.role`.
`bartender` confirmado por el equipo.
Conjunto cerrado: no se crean roles desde la API.

### AccessToken (M) — sin tabla
JWT sin estado. Claims: `sub` (user id), `jti`, `role`, `exp`. Caducidad por
`JWT_EXPIRE_MINUTES`.

### RefreshToken (M) — tabla `refresh_tokens`
`id`, `user_id` (FK), `token_hash` (el valor en claro nunca se guarda),
`expires_at`, `revoked_at` (nulo = vigente), `created_at`.
Caducidad: la fija quien lleve auth/tokens en su spec; se lee de una variable de entorno (p. ej. `JWT_REFRESH_EXPIRE_DAYS`).

### RevokedToken (M) — tabla `revoked_tokens`
`jti` (PK), `expires_at` (cuándo caducaría el access token; luego se puede purgar),
`revoked_at`.

### EmailVerificationToken (S) y PasswordResetToken (S)
Misma forma, dos entidades separadas para mantener el vocabulario: `id`, `user_id`
(FK), `token_hash`, `expires_at`, `used_at` (nulo = no usado), `created_at`.

### SocialAccount (C) — tabla `social_accounts`
`id`, `user_id` (FK), `provider` (`google` / `github`), `provider_user_id`.
Único por (`provider`, `provider_user_id`).

## 3. Relaciones

- `Role` (enum) → `User.role`: un valor por usuario, sin FK
- `User 1:N RefreshToken`
- `User 1:N EmailVerificationToken` · `User 1:N PasswordResetToken` (S)
- `User 1:N SocialAccount` (C)
- `AccessToken` ↔ `RevokedToken`: relación por `jti`, sin FK (el access no se guarda).

**Referencias externas** (definidas en el modelo de P2, no se redefinen aquí):
`Reservation.user_id → User` · `Order.waiter_id → User` · `Category.station` (enum `kitchen`/`bar`) decide qué rol recibe cada ítem: `kitchen` ve estación `kitchen`, `bartender` ve `bar`. Por eso un `User` nunca se
borra físicamente (R-04).

## 4. Reglas de negocio

| Id | Prio | Regla |
|---|---|---|
| R-01 | M | El email es único sin distinguir mayúsculas y se guarda en minúsculas. Duplicado → 409 |
| R-02 | M | Contraseña ≥ 8 caracteres (débil → 422), hash bcrypt; `password_hash` no aparece en ningún schema de salida ni en logs |
| R-03 | M | `POST /auth/register` ignora el rol del payload y crea un `customer`. Solo `admin` crea cuentas `waiter`/`kitchen`/`bartender`/`admin` o cambia roles. El primer admin lo crea `python -m app.scripts.create_admin` |
| R-04 | M | Borrar usuario = `is_active=false`; los inactivos no pueden iniciar sesión. No hay borrado físico |
| R-05 | M | Login correcto emite un par AccessToken + RefreshToken |
| R-06 | M | Rotación: usar un RefreshToken emite un par nuevo y marca `revoked_at` en el usado. Uno ya revocado o caducado → 401 |
| R-07 | M | Logout revoca el RefreshToken actual y añade el `jti` del AccessToken a `RevokedToken`. Un `jti` revocado → 401 en cualquier endpoint |
| R-08 | M | Un usuario desactivado invalida el acceso: sus refresh tokens se rechazan |
| R-09 | S | Los tokens de un solo uso (verificación, recuperación) caducan y se marcan `used_at` al usarse; reutilizar → 400/410 |
| R-10 | S | Rate limiting en login: tras N intentos fallidos desde la misma IP/email → 429 (N y ventana: los fija la spec de la HU de rate limiting, por variable de entorno) |
| R-11 | S | Soft delete: `deleted_at` oculta al usuario de los listados; los cambios registran `updated_by`/`updated_at` |
| R-12 | C | Con `totp_enabled`, el login exige además un código TOTP válido |
| R-13 | C | El login social crea o vincula un `User` (rol `customer`) |
| R-14 | M | La estación de una línea de pedido es la `station` de la categoría de su plato (se deriva en vivo). `kitchen` ve y marca solo líneas `kitchen`; `bartender`, solo `bar`; `admin` y `waiter`, todas. Marcar una línea de otra estación → 403; un pedido sin líneas de su estación no existe para `kitchen`/`bartender` (404). `total` es siempre el del pedido completo |
| R-15 | S | Verificación de email (HU-33), informativa: `email_verified` no impide iniciar sesión. Nace `false` en `POST /auth/register` y `true` en las cuentas creadas por un `admin`, por `create_admin` o por login social (nuevas o vinculadas); pasa a `true` al usar un `EmailVerificationToken` o al fijar la contraseña con un `PasswordResetToken`. Cambiar el propio email lo devuelve a `false` e invalida los `EmailVerificationToken` pendientes. Los endpoints que reciben un email para enviar un enlace (verificación, recuperación) responden igual exista o no la cuenta |
| R-16 | M | El progreso de un pedido se calcula en vivo sobre las líneas que ve el usuario (R-14). `ready_to_serve` de una línea = `prepared_quantity - served_quantity`, nunca menos de 0; el del pedido es la suma de sus líneas. `stage`: `all_served` si todo está servido; si no, `ready_to_serve` si hay unidades listas; si no, `waiting` si no hay nada preparado ni servido; si no, `preparing`. `by_station` repite el cálculo por estación. No cambia el `status` del pedido |

## 5. Pendientes
Ninguno a nivel de ontología. Los parámetros numéricos (caducidad del refresh, límite del rate limiting) los fija la spec de su HU.
La verificación de email quedó resuelta en HU-33 (R-15, definida en `specs/HU-33-verificacion-email.md` y traída aquí para que la citen todas las HU). La recuperación de códigos 2FA se decide en la spec de su HU, que es donde se implementa.
