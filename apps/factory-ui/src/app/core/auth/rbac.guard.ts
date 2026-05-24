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
 * RBAC guard placeholder — canActivate factory function.
 *
 * Phase 10-04: scaffold only — allows all routes through (returns true).
 * Phase 10-05: JwtService injected via RBAC_GUARD_SERVICE_TOKEN to enforce roles.
 *
 * Import path stable: this file is the canonical location.
 * The guard is referenced in app.routes.ts; 10-05 fills the service implementation.
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
  const allowedRoles = (route.data[ROUTE_ROLES_KEY] ?? []) as UserRole[];

  // Attempt to use real service if available (10-05 provides it)
  try {
    const guardService = inject(RBAC_GUARD_SERVICE_TOKEN, { optional: true });

    if (guardService) {
      if (!guardService.isAuthenticated()) {
        router.navigate(['/auth/login']);
        return false;
      }

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
    }
  } catch {
    // Service not yet provided (10-04 scaffold mode) — allow through
  }

  // Scaffold fallback: allow all routes (10-05 wires the real guard)
  return true;
};
