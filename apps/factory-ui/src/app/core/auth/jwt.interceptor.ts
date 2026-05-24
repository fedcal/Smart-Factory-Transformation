import { inject } from '@angular/core';
import {
  HttpInterceptorFn,
  HttpRequest,
  HttpHandlerFn,
} from '@angular/common/http';
import { JwtService } from './jwt.service';

/**
 * URL patterns that require a Bearer token in the Authorization header.
 * Matches /v1/* API routes and /auth/me (profile endpoint).
 * Excludes /auth/login to avoid circular token usage during login.
 */
const BEARER_URL_PATTERNS = ['/v1/', '/auth/me'] as const;

/**
 * Functional HTTP interceptor — attaches JWT Bearer token to API requests.
 *
 * Rules (10-CONTEXT, 10-UI-SPEC):
 *  - Adds `Authorization: Bearer <token>` to requests matching BEARER_URL_PATTERNS
 *  - Does NOT add the header to /auth/login (prevents circular dependency)
 *  - Does NOT modify requests if no token is present (unauthenticated state)
 *  - SSR-safe: JwtService is SSR-safe; token() returns null on server
 */
export const jwtInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
) => {
  const jwtService = inject(JwtService);
  const token = jwtService.getToken();

  if (token && shouldAttachBearer(req.url)) {
    const authorizedReq = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
    return next(authorizedReq);
  }

  return next(req);
};

/**
 * Returns true when the URL matches a protected API pattern.
 */
function shouldAttachBearer(url: string): boolean {
  return BEARER_URL_PATTERNS.some((pattern) => url.includes(pattern));
}
