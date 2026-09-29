# Pedidos360 Backend

Backend Python para catálogo y pedidos de Pedidos360, ejecutado en AWS Lambda detrás de API Gateway HTTP API con JWT Authorizer de Microsoft Entra ID. Serverless (Framework v4) administra la infraestructura; DynamoDB conserva productos y pedidos.

- **Stack desplegado:** `backend-pedidos360-dev` en `us-east-1` (cuenta AWS Academy `559662328432`).
- **URL base:** `https://o3k66b0owk.execute-api.us-east-1.amazonaws.com`

## Arquitectura

```
React + MSAL (frontend)
  → Microsoft Entra ID (login + access token JWT v2)
  → API Gateway HTTP API (JWT Authorizer: firma, iss, aud, exp, scope)
  → AWS Lambda Python 3.14 (roles, scope defensivo, ownership, reglas de negocio)
  → DynamoDB (productos y pedidos; stock atómico)
```

Cada función sigue `handler → service → repository → DynamoDB` (sin Lambda monolítica). Las tablas se llaman `backend-pedidos360-dev-productos` y `backend-pedidos360-dev-pedidos`; `id` es partition key y pedidos usa el GSI `clienteId-index`. No hay tabla de usuarios: la identidad viene de Entra ID (`oid`, fallback `sub`).

## Autenticación y autorización

- **Issuer:** `https://login.microsoftonline.com/4b0c585d-b153-4a09-9342-8df80ff8962b/v2.0`
- **Audience:** `7a88281a-780d-49a9-9cb7-d0bc4333f5c4` (GUID de la App Registration `Pedidos360-API`; **no** `api://...`)
- **Scopes:** `catalog.read`, `catalog.write`, `orders.read`, `orders.write`
- **Roles:** `Admin`, `Operador`, `Cliente`. No existe `Auditor`.

API Gateway valida criptográficamente el JWT antes de invocar la Lambda. La Lambda revalida rol, scope y ownership en cada request (doble barrera). El payload JWT se decodifica en el frontend solo para UX; la seguridad la imponen API Gateway + Lambda.

## Matriz de roles y scopes

| Operación | Roles | Scope |
| --- | --- | --- |
| `GET /catalogo`, `GET /catalogo/{id}` | Admin, Operador | `catalog.read` |
| `POST /catalogo`, `PUT /catalogo/{id}`, `DELETE /catalogo/{id}` | **Admin** | `catalog.write` |
| `GET /pedidos`, `GET /pedidos/{id}` | Admin, Operador, Cliente | `orders.read` |
| `POST /pedidos` | Cliente, Operador | `orders.write` |
| `PUT /pedidos/{id}/estado` | Admin, Operador | `orders.write` |

En código: `_CATALOG_READ_ROLES = {"Admin", "Operador"}` y `_CATALOG_WRITE_ROLES = {"Admin"}` en `src/catalogo/handlers.py`. El Cliente solo ve pedidos cuyo `clienteId` coincide con su `oid` (fallback `sub`); no puede cambiar estados ni administrar el catálogo.

## Endpoints (9 rutas)

| Método y ruta | Lambda | Scope |
| --- | --- | --- |
| `GET /catalogo` | `listarCatalogo` | `catalog.read` |
| `GET /catalogo/{id}` | `obtenerProducto` | `catalog.read` |
| `POST /catalogo` | `crearProducto` | `catalog.write` |
| `PUT /catalogo/{id}` | `actualizarProducto` | `catalog.write` |
| `DELETE /catalogo/{id}` | `eliminarProducto` | `catalog.write` |
| `GET /pedidos` | `listarPedidos` | `orders.read` |
| `GET /pedidos/{id}` | `obtenerPedido` | `orders.read` |
| `POST /pedidos` | `crearPedido` | `orders.write` |
| `PUT /pedidos/{id}/estado` | `actualizarEstadoPedido` | `orders.write` |

Todas las rutas usan el JWT Authorizer `entraJwt` con los scopes indicados. El contrato OpenAPI está en [`docs/openapi.yaml`](docs/openapi.yaml).

## Pedidos y control de stock

- `POST /pedidos` crea el pedido en estado `CREADO` y **no** descuenta stock. El body solo recibe `{ "productos": [{ "productoId", "cantidad" }] }`; la identidad del cliente, `clienteId`, `clienteNombre`, precios y `total` los deriva el backend del JWT y del catálogo. Rechaza campos extra (`clienteId`, `total`, etc.) con 400.
- `CREADO → ACEPTADO` descuenta stock dentro de una transacción DynamoDB que condiciona `stock >= cantidad` y el estado previo; si no hay stock suficiente responde **409 Conflict** y revierte todo.
- `CANCELADO` desde `CREADO` no toca stock; desde `ACEPTADO` o `EN_PREPARACION` devuelve stock una sola vez en la misma transacción. Nunca se permite stock negativo.
- Flujo normal: `CREADO → ACEPTADO → EN_PREPARACION → DESPACHADO → ENTREGADO`. Las transiciones válidas están centralizadas en `src/pedidos/transitions.py`.
- Límite de 99 productos únicos por pedido (máximo de acciones por transacción DynamoDB).

## Códigos HTTP

`200` consulta/actualización, `201` creación, `204` borrado; `400` validación, `401` sin token o token rechazado (API Gateway responde con body vacío antes de Lambda), `403` rol/scope/ownership insuficiente, `404` recurso ausente, `409` transición/stock/conflicto, `500` error controlado genérico (sin stack trace en el body). Los errores de Lambda usan `{ "error": "...", "message": "..." }`.

## Seed de productos de demostración

Los productos con los que el Cliente hace pedidos en la demo deben existir en DynamoDB. El script idempotente `scripts/seed_products.py` inserta los 6 productos demo con IDs estables (`prod-teclado-001` … `prod-soporte-006`) y **no sobrescribe** existentes salvo `--force` explícito:

```powershell
.\.venv\Scripts\python.exe scripts/seed_products.py --dry-run
.\.venv\Scripts\python.exe scripts/seed_products.py
```

El frontend (vista Cliente / "Comprar") usa una fuente de demostración con estos mismos IDs; los pedidos creados desde la UI apuntan a productos reales en DynamoDB.

## Desarrollo local

Requisitos: Python 3.14, AWS CLI v2 configurado, Serverless Framework 4 y Node/npm (frontend).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Las pruebas usan Moto (DynamoDB simulado) y no requieren AWS real. `serverless print --stage dev` valida el template sin desplegar.

## AWS Academy / VocLabs y despliegue

1. Renueva las credenciales temporales en el perfil local `pedidos360` (nunca las subas al repositorio):
   ```powershell
   aws configure set aws_access_key_id "<nueva>" --profile pedidos360
   aws configure set aws_secret_access_key "<nueva>" --profile pedidos360
   aws configure set aws_session_token "<vigente>" --profile pedidos360
   aws sts get-caller-identity --profile pedidos360
   ```
2. Con las credenciales vigentes:
   ```powershell
   serverless.cmd login
   serverless.cmd print --stage dev
   serverless.cmd deploy --stage dev --aws-profile pedidos360
   ```

`provider.iam.role` referencia el rol externo `arn:aws:iam::559662328432:role/LabRole` de AWS Academy. Cambiar credenciales expiradas no requiere modificar código. **No usar `serverless remove`.**

## Pruebas y conexión

`pytest` valida autorización (matriz de roles y scopes), CRUD en DynamoDB simulado, transiciones de pedido, stock atómico, ownership del Cliente y códigos de error. El script [`scripts/test-api.ps1`](scripts/test-api.ps1) permite smoke, preflight, 401 sin token y CRUD/ordenes contra la API live con tokens provistos por variables de entorno; nunca imprime ni almacena tokens.

El frontend conecta con `VITE_API_BASE_URL=https://o3k66b0owk.execute-api.us-east-1.amazonaws.com` desde `http://localhost:5173` (CORS restringido a este origen en dev).

## Documentación del proyecto

- [`docs/openapi.yaml`](docs/openapi.yaml) — contrato de las 9 rutas.
- [`docs/seguridad.md`](docs/seguridad.md) — seguridad y autorización.
- [`docs/pkce.md`](docs/pkce.md) — Authorization Code + PKCE (gestionado por MSAL).
- [`docs/demo-presentacion.md`](docs/demo-presentacion.md) — guion de demo.
- [`docs/rubrica-checklist.md`](docs/rubrica-checklist.md) — checklist de rúbrica.
- [`docs/evidencias/rubrica-final.md`](docs/evidencias/rubrica-final.md) — evidencia final de cierre.