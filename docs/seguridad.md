# Seguridad y autorización

## Responsabilidades

- **Microsoft Entra ID** autentica al usuario y emite tokens para el recurso Pedidos360-API.
- **React/MSAL** gestiona login, caché y adquisición de access tokens; el frontend no es una frontera de seguridad.
- **API Gateway HTTP API** aplica el JWT Authorizer antes de Lambda. AWS valida `kid`/firma con las claves públicas de `jwks_uri`, `iss`, `aud` (o `client_id` si no existe `aud`), `exp`, `nbf`, `iat` y los scopes declarados por ruta. API Gateway cachea las claves públicas hasta dos horas de forma best-effort; no requiere criptografía manual en Lambda.
- **Lambda/Python** recibe los claims que API Gateway validó, extrae `sub`, `oid`, `name`, `preferred_username`, `roles` y `scp`, y comprueba roles, scope, propiedad y reglas de dominio.
- **DynamoDB** aplica condiciones y transacciones para evitar stock negativo, doble transición y devolución duplicada.

La Lambda no vuelve a verificar criptográficamente el JWT. Esto centraliza la validación criptográfica en el JWT Authorizer nativo y evita implementar criptografía propia o confiar en un `decode` sin firma. La frase de la rúbrica que exige que el backend/BFF verifique el JWT queda satisfecha por el componente API Gateway previo a Lambda, pero no por código Python; si se interpreta literalmente como validación dentro del BFF, queda una diferencia de capa que debe consultarse con el profesor. No se desactiva la validación del Authorizer.

El payload del JWT que usa `RequireRole`, `useAuthorization` y TokenInspector en React se decodifica solo para experiencia de usuario/inspección; esa decodificación no verifica legitimidad. El backend y API Gateway siguen siendo obligatorios.

## Issuer y audience pendientes

Configuración de Serverless actual: issuer fallback `https://login.microsoftonline.com/4b0c585d-b153-4a09-9342-8df80ff8962b/v2.0`; audience fallback `api://7a88281a-780d-49a9-9cb7-d0bc4333f5c4`. Ambos se pueden sustituir con `JWT_ISSUER` y `JWT_AUDIENCE` al resolver Serverless.

El valor de `aud` de un access token v2 no se ha inspeccionado. El fallback es histórico, no una afirmación de que coincide. Antes de desplegar, iniciar sesión como usuario real y leer `aud`, `iss`, `scp` y `roles` en TokenInspector. Configurar exactamente esos valores en el entorno de Serverless; nunca cambiar entre GUID y `api://` por conjetura. No copiar ni guardar el token completo.

El JWT Authorizer se asigna a las nueve rutas protegidas. Sin token o con token inválido, API Gateway responde 401 antes de Lambda. Si el token es válido y tiene el scope de API Gateway pero no el rol de negocio, Lambda responde 403. Para demostrar Cliente→403 en catálogo, el token debe incluir `catalog.read`; de lo contrario el rechazo puede ocurrir antes por scope y no demuestra la regla de rol.

## 401 y 403

- **401 Unauthorized**: no hay identidad autenticada o API Gateway rechaza el token (firma, issuer, audience o vigencia).
- **403 Forbidden**: hay identidad autenticada, pero falta rol, scope defensivo o propiedad del pedido.

En el endpoint live inspeccionado, el 401 de API Gateway tiene `Content-Type: application/json` pero body vacío. Ese rechazo sucede antes de Lambda, por lo que no usa el envelope JSON común y no se puede corregir desde los handlers Python. Los errores que sí genera Lambda conservan `{ "error": "...", "message": "..." }`.

Un guard de React solo oculta vistas; un usuario puede llamar directamente la URL. API Gateway y Lambda revalidan autorización en cada request.

## Matriz

| Ruta | Roles en Lambda | Scope API Gateway |
| --- | --- | --- |
| `GET /catalogo`, `GET /catalogo/{id}` | `Admin`, `Operador` | `catalog.read` |
| `POST /catalogo`, `PUT /catalogo/{id}`, `DELETE /catalogo/{id}` | `Admin`, `Operador` actualmente | `catalog.write` |
| `GET /pedidos`, `GET /pedidos/{id}` | `Admin`, `Operador`, `Cliente` | `orders.read` |
| `POST /pedidos` | `Cliente`, `Operador` | `orders.write` |
| `PUT /pedidos/{id}/estado` | `Admin`, `Operador` | `orders.write` |

Cliente ve solo los pedidos cuyo `clienteId` coincide con `oid` (o `sub` si no existe `oid`). Auditor no tiene permiso de rutas de negocio en esta etapa. La diferencia sobre escritura de catálogo está en [decision-conflicts.md](decision-conflicts.md).

## CORS, secretos y logs

La HTTP API restringe origen a `http://localhost:5173`, métodos `GET, POST, PUT, DELETE, OPTIONS` y headers `Authorization, Content-Type, Accept`; no usa wildcard ni credenciales cross-origin. El preflight no lleva JWT y API Gateway lo responde por su configuración CORS. El OPTIONS live desde PowerShell respondió 204 con el origen, métodos y headers esperados; falta evidencia visual en navegador.

Lambda registra operación y request ID, no `event`, headers ni bearer token. Errores no controlados devuelven mensaje genérico sin stack trace en el body. El stack trace se escribe en CloudWatch por `logger.exception`; debe revisarse que los errores de dependencias no incluyan secretos en sus mensajes.

`.env`, credenciales AWS, JWT y tokens no deben subir a GitHub. El TokenInspector puede revelar el access token completo dentro de un `<details>` solo en desarrollo: no mostrarlo en una pantalla compartida ni copiarlo a logs/issues. `LabRole` es un rol IAM preexistente, compartido con AWS Academy, con siete policies administradas y sin policies inline. La cuenta de laboratorio niega `iam:GetPolicy` sobre sus policies VocLab; no se pudo inspeccionar contenido ni confirmar mínimo privilegio. No se alteró ese rol.
