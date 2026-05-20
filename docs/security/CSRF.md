# CSRF Protection Evaluation

**Decision**: CSRF tokens are **not required** for this application.

## Reasoning

CSRF attacks exploit the browser's automatic attachment of session cookies to cross-origin requests. They are only effective against authentication mechanisms that rely on cookies sent automatically by the browser.

Content Engine uses Supabase JWT-based authentication where:

1. All mutation requests (`POST`, `PATCH`, `DELETE`) from the frontend use the `fetch` API with an explicit `Authorization: Bearer <token>` header.
2. The token is stored in `localStorage` or memory by the Supabase client — **never in a cookie that the browser attaches automatically**.
3. A cross-origin attacker cannot read the user's localStorage to extract the JWT (same-origin policy prevents this).
4. Backend scheduler endpoints are protected by a separate `SCHEDULER_SECRET` header, not cookies.

Because no automatic credential attachment occurs, a forged cross-origin request will arrive without the `Authorization` header and be rejected by Supabase RLS and the FastAPI JWT middleware before any data mutation.

## If Cookie-Based Auth Is Added

Should a future change introduce session cookies (e.g., Supabase SSR cookie-based auth for middleware or edge functions), CSRF protection must be revisited. Recommended approach: use the `SameSite=Strict` or `SameSite=Lax` cookie attribute, which mitigates most CSRF vectors without requiring a token.

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Supabase Auth: Token-based vs Cookie-based](https://supabase.com/docs/guides/auth)
