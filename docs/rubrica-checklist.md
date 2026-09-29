# Checklist de rúbrica

Los estados califican evidencia disponible en esta revisión, no configuración del portal o pruebas live no observadas.

| Criterio | Ponderación | Estado | Evidencia | Archivo/configuración | Prueba | Pendiente |
| --- | ---: | --- | --- | --- | --- | --- |
| Rutas de API Gateway y Lambdas | 13% | ⚠️ requiere evidencia/manual | Nueve rutas live con JWT y los scopes esperados; nombres Lambda coinciden con el template | `serverless.yml`, handlers, stack CloudFormation | `get-routes` y nueve Lambdas consultadas; falta ejercicio autenticado de cada ruta | Captura visual API Gateway y resultados CRUD |
| CORS seguro | 7% | ✅ comprobado | Origen `http://localhost:5173`, métodos/headers limitados, sin wildcard | `serverless.yml` | OPTIONS live respondió 204 con origin, methods y headers esperados | Captura navegador para completar evidencia de presentación |
| Tenant, usuarios, roles y políticas | 10% | ⚠️ requiere evidencia/manual | IDs/roles descritos en requisitos y código de autorización | `src/auth/claims.py`, handlers | Tests de roles; no se consultó Entra | Evidencia del tenant, asignaciones y políticas |
| App Registrations, client ID, redirect URI, roles y scopes | 10% | ⚠️ requiere evidencia/manual | Frontend MSAL y `.env.example` contienen el contrato de configuración | `frontend_pedido360/src/auth/authConfig.ts`, `.env.example` | Build frontend pasó; no se inspeccionó portal Entra | Capturas de SPA redirect, API scopes/App Roles y consent |
| Login y obtención de token | 10% | ⚠️ requiere evidencia/manual | MSAL inicializa antes de React y adquiere access token de API | `frontend_pedido360/src/main.tsx`, `src/api/client.ts` | Build pasó; no se ejecutó login | Video/captura con usuario de demo y TokenInspector |
| Authorization Code + PKCE, state y nonce | 15% | ⚠️ requiere evidencia/manual | MSAL Browser gestiona el protocolo; sin PKCE manual | `frontend_pedido360/src/main.tsx`, [pkce.md](pkce.md) | Revisado estáticamente; no hay captura Network | Captura de `code_challenge_method=S256`, `state` y `nonce` sin secretos |
| JWT en todas las rutas, issuer, audience, 200/401/403 | 20% | ⚠️ requiere evidencia/manual | Authorizer JWT y scope en cada route live; issuer v2 esperado; audience live continúa en `api://...` sin comparación con token real | `serverless.yml`, `src/auth/authorization.py` | 401 sin token comprobado live; no hay evidencia real de 200/403 ni `aud` | Claims `aud/iss/scp/roles` de TokenInspector y pruebas autenticadas live |
| Evidencia de nueve rutas y JSON esperado | 15% | ⚠️ requiere evidencia/manual | Contrato OpenAPI y script PowerShell reproducible | [openapi.yaml](openapi.yaml), `scripts/test-api.ps1` | ZIP contiene `src/` y excluye contenido prohibido; no se ejecutó CRUD live | Ejecutar CRUD, guardar status/body saneados y capturas |

## Evidencia local disponible

`python -m compileall src`, `pytest` (62 passed), `serverless print --stage dev` y `serverless package --stage dev --aws-profile pedidos360` pasaron. El ZIP contiene solo archivos `src/`; excluye tests, docs, venv, bytecode y `.env`. El build TypeScript/Vite pasó con aviso de bundle principal superior a 500 kB. AWS confirmó stack `CREATE_COMPLETE`, 9 routes, 9 Lambdas Python 3.14, tablas ACTIVE, 401 sin token y OPTIONS 204.

IAM: `LabRole` tiene 7 policies administradas y 0 inline. AWS Academy denegó `iam:GetPolicy` sobre policies VocLab, así que el contenido/permisos efectivos y el mínimo privilegio no se pudieron auditar; no se modificó el rol.
