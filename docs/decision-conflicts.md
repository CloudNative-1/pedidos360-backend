# Decisiones y alcance

## Escritura de catálogo: solo Admin (RESUELTO)

**Antecedente:** la preferencia del caso era que `POST`, `PUT` y `DELETE` de catálogo fueran solo para `Admin`; el código quedó en `{"Admin", "Operador"}` y existía un conflicto documental.

**Decisión final:** `_CATALOG_WRITE_ROLES = {"Admin"}` en `src/catalogo/handlers.py`. `_CATALOG_READ_ROLES = {"Admin", "Operador"}`.

- Admin: CRUD completo del catálogo.
- Operador: solo lectura (`GET /catalogo` y `GET /catalogo/{id}`); `POST/PUT/DELETE` → **403**.
- Cliente: sin acceso al catálogo administrativo → **403** (y sin ruta en la UI).

Se actualizaron los tests (`tests/test_authorization.py`) y el contrato (`docs/openapi.yaml`), la matriz en `docs/seguridad.md` y el README para reflejar la matriz final.

## Stack original

Los documentos originales citan Angular, Spring Boot/BFF y EC2. El material adaptado del profesor permite React + MSAL y AWS API Gateway + Lambda; el proyecto usa React/TypeScript/Vite, Python Lambda 3.14, API Gateway HTTP API, JWT Authorizer y DynamoDB. No se convirtió a Java, Angular ni EC2.

## JWT en API Gateway frente a BFF

La validación criptográfica, issuer, audience y vigencia se realiza en API Gateway antes de Lambda. Python recibe claims del contexto del authorizer y aplica autorización/reglas (doble barrera). No se implementa criptografía JWT manual en Lambda.

## Roles del modelo final

El modelo definitivo tiene tres roles: `Admin`, `Operador` y `Cliente`. **No existe `Auditor`** en la matriz de esta entrega; un token con cualquier otro rol es rechazado con 403 en todas las rutas (cubierto por tests).