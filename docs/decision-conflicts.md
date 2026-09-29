# Conflictos y diferencias de alcance

## Escritura de catálogo: Admin u Operador

**Caso/requisito entregado:** la preferencia indicada es que `POST`, `PUT` y `DELETE` de catálogo sean solo para `Admin`; además, se exige no cambiar una autorización existente sin reportar el conflicto.

**Material del profesor:** demuestra `Operador + GET /catalogo → 200` y `Cliente + GET /catalogo → 403`. En la guía, la frase “solo Admin puede editar el catálogo” aparece como ejemplo de política por rol, no como una tabla normativa inequívoca para este proyecto.

**Código actual:** permite `Admin` y `Operador` en `catalog.write`; API Gateway además exige el scope `catalog.write`.

**Recomendación:** acordar con el profesor/product owner una única matriz. Si “máxima coherencia” exige que solo Admin modifique catálogo, cambiar `_CATALOG_WRITE_ROLES` a `{"Admin"}` y mantener Operador con lectura; no se hizo ese cambio unilateralmente.

## Stack original

Los documentos originales citan Angular, Spring Boot/BFF y EC2. El material adaptado del profesor permite React + MSAL y AWS API Gateway + Lambda; el proyecto existente usa React/TypeScript/Vite, Python Lambda, API Gateway HTTP API, JWT Authorizer y DynamoDB. Esta adaptación no se convirtió a Java, Angular ni EC2. El HTML de la guía contiene un ejemplo antiguo que describe una Lambda Node.js; el código de esta entrega es Python.

## JWT en API Gateway frente a BFF

La validación criptográfica, issuer, audience y vigencia se realiza en API Gateway antes de Lambda. Python recibe claims del contexto del authorizer y aplica autorización/reglas. Si la rúbrica exige que el proceso BFF/Python valide por sí mismo además del Gateway, eso no está implementado; agregar un verificador local no es necesario para la arquitectura/profesor documentados y requiere acordar interpretación.

## Auditoría

`Auditor` existe como App Role según el equipo, pero la fase de auditoría completa no forma parte del alcance actual. No hay eventos de auditoría, Kafka, reportes ni un endpoint privilegiado para Auditor; el rol no está autorizado en las rutas presentes.
