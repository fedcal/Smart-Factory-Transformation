/**
 * Contract tests for rbacGuard — CR-03 fix verification.
 *
 * Verifies that the guard:
 *   - Denies access (returns false + redirects) when unauthenticated
 *   - Denies access when the role does not match the required roles
 *   - Grants access when the role matches
 *   - Grants access for routes without role restrictions (all authenticated)
 *   - NEVER returns true when authentication fails (no scaffold fallback)
 *
 * CR-03: RBAC_GUARD_SERVICE_TOKEN is now mandatory (no optional injection).
 * A missing provider causes DI to throw, which is the correct failure mode.
 */

import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import {
  rbacGuard,
  RBAC_GUARD_SERVICE_TOKEN,
  ROUTE_ROLES_KEY,
  UserRole,
} from './rbac.guard';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeRoute(roles: UserRole[] | undefined): ActivatedRouteSnapshot {
  const snapshot = new ActivatedRouteSnapshot();
  // ActivatedRouteSnapshot.data is read-only in runtime; cast to write in tests
  (snapshot as unknown as { data: Record<string, unknown> }).data = roles
    ? { [ROUTE_ROLES_KEY]: roles }
    : {};
  return snapshot;
}

const fakeState = {} as RouterStateSnapshot;

function runGuard(
  route: ActivatedRouteSnapshot,
  isAuthenticated: boolean,
  currentRole: UserRole | null,
): boolean {
  return TestBed.runInInjectionContext(() =>
    rbacGuard(route, fakeState),
  ) as boolean;
}

// ---------------------------------------------------------------------------
// Test suites
// ---------------------------------------------------------------------------

describe('rbacGuard — CR-03: no scaffold fallback, mandatory token', () => {
  let router: Router;
  let navigateSpy: jest.Mock;

  function setup(isAuthenticated: boolean, currentRole: UserRole | null): void {
    TestBed.configureTestingModule({
      providers: [
        {
          provide: Router,
          useValue: { navigate: jest.fn() },
        },
        {
          provide: RBAC_GUARD_SERVICE_TOKEN,
          useValue: {
            isAuthenticated: () => isAuthenticated,
            getCurrentRole: () => currentRole,
          },
        },
      ],
    });
    router = TestBed.inject(Router);
    navigateSpy = router.navigate as jest.Mock;
  }

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  // ---------------------------------------------------------------------------
  // Unauthenticated — must DENY and redirect
  // ---------------------------------------------------------------------------

  it('denies access and redirects to /auth/login when not authenticated', () => {
    setup(false, null);
    const result = TestBed.runInInjectionContext(() =>
      rbacGuard(makeRoute(['operator']), fakeState),
    );
    expect(result).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(['/auth/login']);
  });

  it('never returns true when unauthenticated (CR-03: no scaffold fallback)', () => {
    setup(false, null);
    const result = TestBed.runInInjectionContext(() =>
      rbacGuard(makeRoute([]), fakeState),
    );
    expect(result).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // Authenticated but wrong role — must DENY
  // ---------------------------------------------------------------------------

  it('denies access when authenticated user has wrong role', () => {
    setup(true, 'operator');
    const result = TestBed.runInInjectionContext(() =>
      rbacGuard(makeRoute(['admin']), fakeState),
    );
    expect(result).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith(['/auth/login']);
  });

  it('denies access when role is null even for a restricted route', () => {
    setup(true, null);
    const result = TestBed.runInInjectionContext(() =>
      rbacGuard(makeRoute(['operator']), fakeState),
    );
    expect(result).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // Authenticated with correct role — must GRANT
  // ---------------------------------------------------------------------------

  it('grants access when authenticated user has the required role', () => {
    setup(true, 'operator');
    const result = TestBed.runInInjectionContext(() =>
      rbacGuard(makeRoute(['operator']), fakeState),
    );
    expect(result).toBe(true);
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it('grants access when user role is one of multiple allowed roles', () => {
    setup(true, 'shift-supervisor');
    const result = TestBed.runInInjectionContext(() =>
      rbacGuard(makeRoute(['shift-supervisor', 'manager']), fakeState),
    );
    expect(result).toBe(true);
  });

  // ---------------------------------------------------------------------------
  // Route with no role restriction — all authenticated users may pass
  // ---------------------------------------------------------------------------

  it('grants access for routes with no role restriction (e.g. /demo)', () => {
    setup(true, 'operator');
    const result = TestBed.runInInjectionContext(() =>
      rbacGuard(makeRoute(undefined), fakeState),
    );
    expect(result).toBe(true);
    expect(navigateSpy).not.toHaveBeenCalled();
  });

  it('grants access for routes with empty roles array when authenticated', () => {
    setup(true, 'manager');
    const result = TestBed.runInInjectionContext(() =>
      rbacGuard(makeRoute([]), fakeState),
    );
    expect(result).toBe(true);
  });
});
