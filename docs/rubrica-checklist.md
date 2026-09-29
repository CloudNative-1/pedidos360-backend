# Checklist de rúbrica

Estado al cierre de la entrega (`final/rubrica-pedidos360`). Los ítems marcados como evidencia manual requieren comprobación en navegador/Entra/AWS durante la presentación (ver [evidencias/rubrica-final.md](evidencias/rubrica-final.md)).

| Criterio | Estado | Evidencia actual | Evidencia manual pendiente |
| --- | --- | --- | --- |
| 9 rutas + 9 Lambdas con JWT Authorizer y scopes | ✅ configuración verificada | `serverless.yml` desplegado como `backend-pedidos360-dev`; 9 rutas, 9 Lambdas Python 3.14 | Ejercer cada ruta autenticada live |
| CORS seguro | ✅ comprobado | Origen `http://localhost:5173`, métodos/headers limitados, sin wildcard | Captura navegador |
| Tenant, roles y políticas | ✅ matriz implementada | Rol Claims en Lambda: Admin/Operador/Cliente sin Auditor; tests 403 para roles ajenos | Evidencia de asignaciones en portal Entra |
| App Registrations, redirect URI, scopes | ✅ configurado | `authConfig.ts` + `.env.example` | Capturas del portal Entra |
| Login y obtención de token | ✅ implementado | MSAL inicializa antes de React; access token vía `acquireTokenSilent` | Video/captura de login real |
| Authorization Code + PKCE, state, nonce | ✅ implementado (MSAL) | `src/main.tsx`, docs/pkce.md | Captura Network con `response_type=code`, `code_challenge_method=S256`, `state`, `nonce` |
| JWT, issuer, audience, 200/401/403 | ✅ configuración + 401 live | Issuer v2 + audience GUID en `serverless.yml`; 401 sin token comprobado live | 200/403 autenticados live y claims `aud/iss/scp/roles` en TokenInspector |
| Evidencia de 9 rutas y JSON esperado | ✅ contrato | OpenAPI actualizado; `scripts/test-api.ps1` reproducible | CRUD live con status/body saneados |
| Tests | ✅ **64 passed** | `pytest -q` en venv local (Moto) | — |
| Build frontend | ✅ aprobado | `npm run build` (aviso de bundle >500 kB no bloqueante) | — |
| Lint frontend | ✅ aprobado | `npm run lint` (oxlint) | — |

## Verificado en esta revisión

- `python -m compileall src` y `pytest -q` → **64 passed** (matriz de roles/scopes, CRUD, transiciones, stock atómico, ownership Cliente, 401/403/409).
- `serverless print --stage dev` resuelve el template; stack `backend-pedidos360-dev` desplegado en `us-east-1` con URL `https://o3k66b0owk.execute-api.us-east-1.amazonaws.com`.
- 401 sin token y OPTIONS 204 (CORS) comprobados contra la API live.
- `_CATALOG_WRITE_ROLES = {"Admin"}`; roles finales Admin/Operador/Cliente (sin Auditor).

## No auditable desde este entorno

- Las policies del `LabRole` de AWS Academy (`iam:GetPolicy` denegado); no se modificó el rol.
- La cuenta Entra ID real y los claims de un access token emitido (evidencia manual).