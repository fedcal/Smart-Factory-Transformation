import { Route } from '@angular/router';
import { rbacGuard, UserRole } from '../../core/auth/rbac.guard';

/**
 * Demo feature routes — lazy loaded.
 *
 * /demo → PersonaWalkthroughComponent (all authenticated roles — roles: [])
 *
 * T-10-09-02: /demo open to all authenticated personas by design (dev walkthrough).
 * Embeds only data the logged-in role may already see.
 *
 * Linked from app.routes.ts via loadChildren.
 */
export const demoRoutes: Route[] = [
  {
    path: '',
    loadComponent: () =>
      import('./persona-walkthrough.component').then(
        (m) => m.PersonaWalkthroughComponent,
      ),
    canActivate: [rbacGuard],
    data: { roles: [] as UserRole[] }, // [] = any authenticated role
    title: 'Demo Persona — Smart Factory',
  },
];
