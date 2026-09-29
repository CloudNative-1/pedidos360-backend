# OAuth 2.0, OIDC y PKCE

Pedidos360-Frontend es una SPA pública, sin `client_secret`. `@azure/msal-browser` implementa Authorization Code Flow con PKCE; el código de negocio no genera manualmente `code_verifier` ni `code_challenge`. En `src/main.tsx`, `PublicClientApplication.initialize()` termina antes de renderizar React. `loginRequest` usa `openid` y `profile`; el token de API se solicita mediante `acquireTokenSilent` y MSAL gestiona el fallback interactivo, su caché y los redirects.

MSAL también administra `state` (correlación/mitigación CSRF del redirect) y `nonce` (vinculación del ID token a la autenticación). No se debe copiar ni implementar manualmente esos valores. El ID token representa autenticación del usuario en el cliente; el access token pedido para los scopes de Pedidos360-API autoriza llamadas a la API.

## Cómo demostrarlo

1. Abrir DevTools → Network y filtrar solicitudes a `login.microsoftonline.com` al iniciar sesión.
2. En la solicitud de autorización comprobar `response_type=code`, `code_challenge`, `code_challenge_method=S256` y `state`; `nonce` forma parte del protocolo OIDC.
3. Mostrar `src/main.tsx` para `initialize()` y `src/api/client.ts` para adquisición del access token y header Bearer.
4. Mostrar TokenInspector con solo claims `aud`, `iss`, `scp`, `roles`, `sub`, `exp`; ocultar el token completo y datos personales durante la presentación.

No se registró una traza de navegador de login en esta auditoría; la descripción se apoya en el código/configuración MSAL y requiere evidencia manual del tenant.
