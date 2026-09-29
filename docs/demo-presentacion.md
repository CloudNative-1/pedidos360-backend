# Guion de demostración (7–9 minutos)

No muestres tokens completos, credenciales, direcciones personales ni datos de otros usuarios. Prepara usuarios Admin, Operador y Cliente asignados en Entra; no se asumen cuentas disponibles. Confirma antes de la clase los claims reales y audience.

| Tiempo | Abrir/mostrar | Acción y explicación |
| --- | --- | --- |
| 0:00–0:45 | Este README, sección Arquitectura | React/MSAL → Entra ID → access token → API Gateway JWT Authorizer → Lambdas Python → DynamoDB. Aclara la adaptación aprobada del stack original. |
| 0:45–1:40 | Portal Entra: Overview de Pedidos360-Frontend y Pedidos360-API | Mostrar IDs, SPA redirect `http://localhost:5173`, scopes `catalog.read`, `catalog.write`, `orders.read`, `orders.write` y roles existentes. Ocultar datos de cuenta. |
| 1:40–2:20 | React corriendo en `http://localhost:5173` | Login y logout MSAL; decir que MSAL maneja Authorization Code + PKCE, `state` y `nonce`, no código manual. |
| 2:20–3:00 | TokenInspector | Mostrar solo `aud`, `iss`, `scp`, `roles`, `sub`, `exp`. Comparar `aud` y `iss` con Serverless; no abrir el detalle del token completo. |
| 3:00–3:45 | API Gateway HTTP API → Routes/Authorizers y CORS | Mostrar las nueve rutas, JWT Authorizer y scopes; CORS limitado a origen dev. Explicar que el preflight OPTIONS no lleva bearer token. |
| 3:45–4:30 | PowerShell: `scripts/test-api.ps1 -Scenario NoToken`, luego Authorization | Sin token `/catalogo` da 401. Admin/Operador con scope da 200. Cliente con `catalog.read` en token debe llegar a Lambda y dar 403 por rol. |
| 4:30–5:20 | API `/catalogo` y UI Catálogo | Consultar catálogo y explicar 200. Si el profesor pide escritura, describir el conflicto de autorización Operador vs Admin. |
| 5:20–6:40 | PowerShell: `scripts/test-api.ps1 -Scenario OrderFlow` | Cliente crea pedido CREADO; mostrar stock sin decremento, Admin acepta y stock baja, avanza a preparación, cancela y stock se restaura. |
| 6:40–7:30 | DynamoDB Tables / Items | Mostrar claves `id`, GSI `clienteId-index`, estado y stock. No editar ni borrar datos de demo ajenos. |
| 7:30–8:15 | Tests locales: `pytest` y `docs/rubrica-checklist.md` | Mostrar Moto local, resultado actual y evidencia AWS/Entra aún requerida. |
| 8:15–9:00 | `docs/decision-conflicts.md` | Explicar la adaptación Angular/Spring a React/Python Lambda y la decisión pendiente de escritura de catálogo. |

## Orden de preparación

1. Actualizar credenciales temporales del perfil AWS `pedidos360`; no iniciar deploy durante la presentación. Si PowerShell bloquea el script local, permitir scripts solo en la sesión actual con `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.
2. Confirmar audience, issuer, scopes y roles del access token real en TokenInspector; revisar que coincidan con Serverless.
3. Confirmar `VITE_API_BASE_URL`, permisos de consentimiento y CORS real antes de entrar al navegador.
4. Crear o identificar usuarios de prueba Admin, Operador y Cliente. Para demostrar 403 por rol, el Cliente debe tener `catalog.read` consentido para que API Gateway no rechace primero por scope.
5. Ejecutar `scripts/test-api.ps1 -Scenario Preflight`, `NoToken`, `Authorization`, `CatalogCrud` y `OrderFlow`; guardar respuestas sin tokens ni datos personales.
