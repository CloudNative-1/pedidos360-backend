# Evidencia final — Rubrica Pedidos360

Fecha de cierre: 2026-09-29 · Ramas: `final/rubrica-pedidos360` (frontend y backend).

Este documento usa casillas para registrar la evidencia de la presentación. Los ítems marcados
**✅ verificada** ya fueron comprobados de forma automatizada o estática en esta entrega; los que
quedan en **⬜** requieren evidencia manual (navegador, portal Entra o AWS) y deben marcarse en la demo.
**No incluir tokens, credenciales ni secretos.**

## Autenticación (Entra ID)

- [ ] Login real con Microsoft Entra ID (MSAL, `prompt: select_account`)
- [ ] Cambio de cuenta (login con cuenta distinta)
- [ ] Logout
- [ ] No mocks: usuario real, sin selector falso de rol
- [ ] PKCE: `response_type=code`, `code_challenge`, `code_challenge_method=S256`, `state`, `nonce` (DevTools/Network)
- [ ] Claims vistos en TokenInspector: `oid`, `name`, `preferred_username`, `roles`, `scp`

## JWT / API Gateway

| Ítem | Valor esperado | Estado |
| --- | --- | --- |
| Issuer | `https://login.microsoftonline.com/4b0c585d-b153-4a09-9342-8df80ff8962b/v2.0` | ✅ configuración |
| Audience | `7a88281a-780d-49a9-9cb7-d0bc4333f5c4` (GUID, no `api://`) | ✅ configuración |
| Scopes | `catalog.read`, `catalog.write`, `orders.read`, `orders.write` | ✅ configuración |
| JWT Authorizer en las 9 rutas | `serverless.yml` `entraJwt` | ✅ configuración |
| CORS | origen `http://localhost:5173`, sin wildcard | ✅ comprobado live (OPTIONS 204) |
| `GET /catalogo` sin token → **401** | body vacío de API Gateway | ✅ comprobado live |

## Matriz de autorización

| Prueba | Usuario | Esperado | Estado |
| --- | --- | --- | --- |
| `GET /catalogo` | Admin | 200 | ⬜ manual (automatizable) |
| `GET /catalogo` | Operador | 200 | ⬜ manual |
| `GET /catalogo` | Cliente | 403 | ⬜ manual |
| `POST /catalogo` | Admin | 201 | ⬜ manual |
| `POST /catalogo` | Operador | 403 | ⬜ manual |
| `PUT /catalogo/{id}` | Operador | 403 | ⬜ manual (cubierto en pytest) |
| `DELETE /catalogo/{id}` | Operador | 403 | ⬜ manual (cubierto en pytest) |
| `POST /pedidos` | Cliente | 201 | ⬜ manual |
| `POST /pedidos` | Operador | 201 | ⬜ manual |
| `PUT /pedidos/{id}/estado` | Cliente | 403 | ✅ cubierto en pytest |
| `PUT /pedidos/{id}/estado` | Operador | 200 | ✅ cubierto en pytest |
| Ownership: Cliente solo ve sus pedidos | Cliente | 200 filtrado por `clienteId` | ✅ cubierto en pytest |

## Smoke test funcional (orden de presentación)

- [ ] **Admin:** login real → Panel de Administración → Catálogo → crear producto → editar → listar
- [ ] **DynamoDB:** producto creado presente en `backend-pedidos360-dev-productos`
- [ ] **Cliente:** cambiar cuenta → login → Inicio Cliente → Comprar → seleccionar producto(s) demo reales → crear pedido → estado `CREADO` → Mis pedidos (solo los propios)
- [ ] **DynamoDB:** pedido presente en `backend-pedidos360-dev-pedidos` con `clienteId`, estado y total correctos
- [ ] **Operador:** cambiar cuenta → login → Panel de Operaciones → Catálogo solo lectura (sin botones de edición) → Pedidos → aceptar pedido del Cliente (`CREADO → ACEPTADO`)
- [ ] **Stock:** tras ACEPTADO, stock disminuyó en DynamoDB (regla: `CREADO` no descuenta; `ACEPTADO` sí, atómico, 409 si no hay stock)

## Transiciones de estado

- [ ] `CREADO → ACEPTADO → EN_PREPARACION → DESPACHADO → ENTREGADO` (reglas del backend)
- [ ] `CANCELADO` desde estado que ya descontó stock devuelve stock una sola vez
- [ ] `CANCELADO` desde `CREADO` no toca stock

## Calidad y entrega

- [ ] `pytest -q` → 64 passed (backend, Moto)
- [ ] `npm run lint` (frontend, oxlint)
- [ ] `npm run build` (frontend, aviso de bundle no bloqueante)
- [ ] `git diff --check` limpio en ambos repos
- [ ] OpenAPI describe las 9 rutas y la matriz final (`docs/openapi.yaml`)
- [ ] README frontend y backend actualizados
- [ ] Sin secretos en el repositorio (`.env`, credenciales AWS, JWT, tokens ausentes)
- [ ] Frontend en `final/rubrica-pedidos360` pushado; backend en `final/rubrica-pedidos360` pushado; sin merge a `main`