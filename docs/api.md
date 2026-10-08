# RestoAPI · Documentación de la API

La referencia completa e interactiva está en Swagger (`/docs`). Este documento resume el
contrato por módulo. Formatos comunes:

- **Errores:** `{"detail": str, "code": str}` en todas las respuestas de error (HU-11).
  - Validación de datos (`422`): `{"detail": "Invalid request data", "code": "validation_error",
    "errors": [{"loc": [...], "msg": str, "type": str}]}`. `errors` indica qué campo falla.
  - Error inesperado (`500`): `{"detail": "Internal server error", "code": "internal_error"}`.
  - Codes genéricos: `not_found` (404), `conflict` (409), `forbidden` (403), `unauthorized`
    (401), `method_not_allowed` (405), `unprocessable` (422 de reglas de negocio).
- **Listados paginados:** `{"items": [], "total": int, "page": int, "size": int}` con
  `?page` (≥ 1, por defecto 1) y `?size` (1..100, por defecto 20)
- **Autenticación:** cabecera `Authorization: Bearer <token>`. Sin token o con un token
  no válido → `401`. Rol sin permiso → `403`.

<!-- TODO(Rita, R-08): completar el resto de módulos. -->

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

## Reservas (`/reservations`) · HU-10, HU-19

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
`notes` y `status`. Si cambia la mesa, la hora, la duración o las personas, se revalidan el aforo
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