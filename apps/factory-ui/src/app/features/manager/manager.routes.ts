import { Route } from '@angular/router';
import { rbacGuard, UserRole } from '../../core/auth/rbac.guard';

/**
 * Manager feature routes — plan 10-08.
 *
 * Provides the lazy-loadable route set for the /manager persona area (Sala Controllo).
 * Consumed by app.routes.ts via loadChildren.
 *
 * RBAC: shift-supervisor and manager roles may access this area (T-10-08-01).
 */
export const managerRoutes: Route[] = [
  {
    path: '',
    loadComponent: () =>
      import('./manager.component').then((m) => m.ManagerComponent),
    canActivate: [rbacGuard],
    data: { roles: ['shift-supervisor', 'manager'] as UserRole[] },
    title: 'Sala Controllo — Smart Factory',
  },
];
