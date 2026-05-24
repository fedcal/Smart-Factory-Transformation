import { Route } from '@angular/router';
import { rbacGuard, UserRole } from '../../core/auth/rbac.guard';

/**
 * Technician feature routes — lazy loaded.
 *
 * /technician → TechnicianComponent (roles: technician)
 *
 * Linked from app.routes.ts via loadChildren.
 */
export const technicianRoutes: Route[] = [
  {
    path: '',
    loadComponent: () =>
      import('./technician.component').then((m) => m.TechnicianComponent),
    canActivate: [rbacGuard],
    data: { roles: ['technician'] as UserRole[] },
    title: 'Area Tecnica — Smart Factory',
  },
];
