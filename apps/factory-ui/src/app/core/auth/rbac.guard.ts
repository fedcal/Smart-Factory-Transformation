import {
  inject,
  Injectable,
  InjectionToken,
} from '@angular/core';
import {
  CanActivateFn,
  ActivatedRouteSnapshot,
  RouterStateSnapshot,
  Router,
} from '@angular/router';

/**
 * User role type — matches JWT payload `role` claim (UI-SPEC seeded persona users).
 * Full list: operator | technician | shift-supervisor | manager | admin
 */
export type UserRole =
  | 'operator'
  | 'technician'
  | 'shift-supervisor'
  | 'manager'
  | 'admin';

/**
 * Route data key for allowed roles.
 * Usage in route config:
 *   data: { roles: ['operator'] as UserRole[] }
 */
export const ROUTE_ROLES_KEY = 'roles';

/**
 * Injection token for the RBAC guard dependency.
 * Allows JwtService (plan 10-05) to be injected without circular dependencies.
 * Plan 10-05 provides RBAC_GUARD_SERVICE_TOKEN with the real JwtService.
 */
export const RBAC_GUARD_SERVICE_TOKEN = new InjectionToken<{
  getCurrentRole(): UserRole | null;
  isAuthenticated(): boolean;
}>('SFT_RBAC_GUARD_SERVICE');

/**
 * RBAC guard — canActivate factory function.
 *
 * RBAC_GUARD_SERVICE_TOKEN is mandatory: inject() without { optional: true }
 * causes Angular DI to throw if the token is not provided in app.config.ts.
 * This is intentional — a missing provider is a misconfiguration that must
 * fail loudly (never silently grant access). CR-03 fix: removed scaffold
 * fallback that returned true when the service was absent.
 *
 * Authorized roles per route (UI-SPEC):
 *   /operator   → ['operator']
 *   /technician → ['technician']
 *   /manager    → ['shift-supervisor', 'manager']
 *   /admin      → ['admin']
 *   /demo       → all authenticated roles
 */
export const rbacGuard: CanActivateFn = (
  route: ActivatedRouteSnapshot,
  _state: RouterStateSnapshot,
): boolean => {
  const router = inject(Router);
  // Mandatory injection — throws if RBAC_GUARD_SERVICE_TOKEN is not provided.
  // On genuine DI error the application fails loudly; it must never fall back
  // to granting access (CR-03).
  const guardService = inject(RBAC_GUARD_SERVICE_TOKEN);

  if (!guardService.isAuthenticated()) {
    router.navigate(['/auth/login']);
    return false;
  }

  const allowedRoles = (route.data[ROUTE_ROLES_KEY] ?? []) as UserRole[];
  if (allowedRoles.length === 0) {
    // No role restriction (e.g. /demo — all authenticated)
    return true;
  }

  const currentRole = guardService.getCurrentRole();
  if (currentRole && allowedRoles.includes(currentRole)) {
    return true;
  }

  // 403 — not authorized for this persona area
  router.navigate(['/auth/login']);
  return false;
};
