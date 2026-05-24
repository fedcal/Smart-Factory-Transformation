import { Route } from '@angular/router';
import { rbacGuard, UserRole } from '../../core/auth/rbac.guard';

/**
 * Admin feature routes — lazy loaded.
 *
 * /admin → AdminComponent (roles: admin)
 *
 * Linked from app.routes.ts via loadChildren.
 * Security: T-10-09-01 — rbac-guarded to admin role; backend is authoritative.
 */
export const adminRoutes: Route[] = [
  {
    path: '',
    loadComponent: () =>
      import('./admin.component').then((m) => m.AdminComponent),
    canActivate: [rbacGuard],
    data: { roles: ['admin'] as UserRole[] },
    title: 'Amministrazione — Smart Factory',
  },
];
