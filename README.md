# Pedidos360 Backend

Backend Python existente para catálogo y pedidos, ejecutado en AWS Lambda detrás de API Gateway HTTP API. Serverless administra la configuración; DynamoDB conserva productos y pedidos. El stack desplegado que reporta el equipo es `backend-pedidos360-dev` en `us-east-1`, con URL `https://o3k66b0owk.execute-api.us-east-1.amazonaws.com`.

## Arquitectura

`React + MSAL` inicia sesión con Microsoft Entra ID y solicita un access token de `Pedidos360-API`. El navegador manda `Authorization: Bearer <access_token>` a API Gateway. Su JWT Authorizer valida firma, `iss`, `aud`, `exp` y el scope configurado por ruta antes de invocar la Lambda. El handler extrae los claims validados, aplica roles/ownership y llama al service; el service contiene reglas de negocio y el repository accede a DynamoDB.

Cada función sigue `handler → service → repository → DynamoDB`; no hay Lambda monolítica. Las tablas se llaman `backend-pedidos360-dev-productos` y `backend-pedidos360-dev-pedidos`; `id` es partition key y pedidos tiene el GSI `clienteId-index`. No se requiere tabla de usuarios: la identidad viene de Entra ID.

## Identidad y permisos

Tenant informado: `4b0c585d-b153-4a09-9342-8df80ff8962b`. El frontend y la API son App Registrations distintas. El access token debe ser para la API, no un ID token ni un token de Microsoft Graph. MSAL Browser obtiene/cacha el token; no se guarda manualmente en archivos del backend.

Scopes exactos: `catalog.read`, `catalog.write`, `orders.read`, `orders.write`. Roles exactos: `Admin`, `Operador`, `Cliente`, `Auditor`. El código no implementa auditoría completa; `Auditor` no autoriza rutas de negocio actuales.

El issuer configurado por defecto es el issuer v2 esperado: `https://login.microsoftonline.com/4b0c585d-b153-4a09-9342-8df80ff8962b/v2.0`. El fallback actual de audience es `api://7a88281a-780d-49a9-9cb7-d0bc4333f5c4`; es el valor histórico de configuración, **no está confirmado contra el access token v2 real**. No desplegar hasta comparar `aud`, `iss`, `scp` y `roles` en TokenInspector. `JWT_ISSUER` y `JWT_AUDIENCE` son variables de resolución Serverless y pueden sobrescribir ambos valores. Ver [seguridad](docs/seguridad.md).

Roles por operación:

| Operación | Roles | Scope | Regla adicional |
| --- | --- | --- | --- |
| GET catálogo y producto | Admin, Operador | `catalog.read` | Cliente obtiene 403 |
| POST/PUT/DELETE catálogo | Admin, Operador | `catalog.write` | Existe conflicto documental sobre permitir escritura a Operador; no se cambió silenciosamente |
| GET pedidos y pedido | Admin, Operador, Cliente | `orders.read` | Cliente solo ve sus pedidos |
| POST pedido | Cliente, Operador | `orders.write` | Cliente/identidad se deriva del JWT; precio/total de backend |
| PUT estado pedido | Admin, Operador | `orders.write` | Cliente no cambia estados |

La diferencia del permiso de escritura del catálogo está registrada en [conflictos de requisitos](docs/decision-conflicts.md). `Auditor` existe en Entra según el equipo, pero está fuera del alcance de endpoints actual.

## Rutas

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

Todas las rutas anteriores tienen el JWT Authorizer. La configuración exacta está en `serverless.yml`; el contrato está en [OpenAPI](docs/openapi.yaml).

## Stock y pedidos

Crear pedido genera estado `CREADO` y no descuenta stock. La transición `CREADO → ACEPTADO` descuenta dentro de una transacción DynamoDB que condiciona `stock >= cantidad` y condiciona el estado previo del pedido. Si falla una línea, DynamoDB revierte la transacción completa y el backend devuelve 409. Cancelar desde `CREADO` no toca stock; cancelar desde `ACEPTADO` o `EN_PREPARACION` devuelve stock en la misma transacción que marca el pedido `CANCELADO`. Las transiciones están centralizadas en `src/pedidos/transitions.py`.

El endpoint rechaza más de 99 productos únicos: la transacción requiere una acción por producto y otra por pedido, frente al máximo DynamoDB de 100 acciones.

## Códigos HTTP

`200` consulta/actualización, `201` creación, `204` borrado; `400` validación, `401` falta principal, `403` rol/scope/ownership, `404` elemento ausente, `409` transición/stock/conflicto y `500` error no controlado. En la API live observada, API Gateway devuelve 401 con body vacío antes de invocar Lambda. Los errores generados por Lambda tienen `{ "error": "...", "message": "..." }`; el 500 no devuelve stack trace en el body. El logger registra operación/request ID, no el evento ni el bearer token.

## Desarrollo local

Requisitos comprobados en este entorno: Python 3.14 y AWS Lambda `python3.14` aparece como runtime soportado; Node/npm para el frontend separado. No se requiere AWS para las pruebas de backend: Moto simula DynamoDB.

```powershell
cd backend-pedidos360
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m compileall src
.\.venv\Scripts\pytest.exe
serverless.cmd print --stage dev
```

`requirements.txt` no declara librerías runtime propias; el código usa `boto3` del runtime Lambda. `requirements-dev.txt` aporta `pytest` y `moto[dynamodb]`. El paquete se limita a `src/` y excluye bytecode/cache, tests y docs.

## AWS Academy y Serverless

Renueva las credenciales temporales en el perfil local `pedidos360`; no las guardes en el repositorio ni las pegues en chats. Configúralas localmente con `aws configure --profile pedidos360` y agrega el session token vigente con `aws configure set aws_session_token <valor-local> --profile pedidos360`. Verifica primero `aws sts get-caller-identity --profile pedidos360`.

Después de confirmar `JWT_ISSUER`/`JWT_AUDIENCE` contra el token real y revisar el diff de infraestructura:

```powershell
serverless.cmd print --stage dev
serverless.cmd package --stage dev --aws-profile pedidos360
serverless.cmd deploy --stage dev --aws-profile pedidos360
```

El último comando **no se ha ejecutado**. No uses `serverless remove`. `provider.iam.role` referencia el rol externo `arn:aws:iam::559662328432:role/LabRole`; no se declara su policy en este proyecto, por lo que el mínimo privilegio efectivo no se puede comprobar aquí y depende de AWS Academy. Actualizar credenciales expiradas no requiere cambiar código.

## Pruebas y conexión

`pytest` valida autorización, CRUD en DynamoDB simulado, estados, stock atómico, errores y ownership; no valida una cuenta Entra o recursos AWS reales. El script [test-api.ps1](scripts/test-api.ps1) permite hacer smoke, preflight y CRUD con tokens proporcionados localmente mediante `PEDIDOS360_TOKEN_ADMIN`/`PEDIDOS360_TOKEN_CLIENTE`; nunca imprime ni almacena tokens. Si PowerShell bloquea scripts por la política local, habilítalos solo para esa sesión con `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` y luego ejecuta `scripts/test-api.ps1`.

Para el frontend separado, configura su `.env` local con `VITE_API_BASE_URL=https://o3k66b0owk.execute-api.us-east-1.amazonaws.com` y los scopes de `Pedidos360-API`. En el entorno inspeccionado el `.env` tenía los cuatro scopes y Client/Tenant IDs configurados, pero `VITE_API_BASE_URL` estaba vacío. No se modificó el frontend porque la ruta con JWT real y la audience todavía no se han verificado. Ejecuta `npm.cmd run build` desde `frontend_pedido360` en PowerShell.

El material original menciona Angular/Spring Boot y el ejemplo HTML también contiene una referencia antigua a Lambda Node.js. El material adaptado permite React + Lambda; la implementación actual es React/TypeScript/Vite/MSAL + Python Lambda, API Gateway HTTP API y DynamoDB. No hay RabbitMQ/Kafka/Zookeeper, reportes ni auditoría completa en esta fase. Ver [PKCE](docs/pkce.md), [guía de demo](docs/demo-presentacion.md) y [checklist de rúbrica](docs/rubrica-checklist.md).
