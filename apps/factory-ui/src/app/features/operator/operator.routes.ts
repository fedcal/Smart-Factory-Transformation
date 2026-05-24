import { Route } from '@angular/router';
import { rbacGuard, UserRole } from '../../core/auth/rbac.guard';

/**
 * Operator feature routes — plan 10-08.
 *
 * Provides the lazy-loadable route set for the /operator persona area.
 * Consumed by app.routes.ts via loadChildren.
 *
 * RBAC: only 'operator' role may access this area (T-10-08-01 Elevation of Privilege).
 */
export const operatorRoutes: Route[] = [
  {
    path: '',
    loadComponent: () =>
      import('./operator.component').then((m) => m.OperatorComponent),
    canActivate: [rbacGuard],
    data: { roles: ['operator'] as UserRole[] },
    title: 'Area Operatore — Smart Factory',
  },
];
