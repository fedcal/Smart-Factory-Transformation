import { Route } from '@angular/router';
import { rbacGuard, UserRole } from './core/auth/rbac.guard';

/**
 * Application route map — Phase 10-09 (final)
 *
 * All 5 persona areas wired to real feature routes via loadChildren.
 * No placeholder routes remain.
 *
 * Structure:
 *   /auth/login        — public login page
 *   /                  — AppShell layout route
 *     /operator        → operator.routes.ts  (roles: operator)        [10-08]
 *     /technician      → technician.routes.ts (roles: technician)     [10-09]
 *     /manager         → manager.routes.ts   (roles: shift-supervisor, manager) [10-08]
 *     /admin           → admin.routes.ts     (roles: admin)           [10-09]
 *     /demo            → demo.routes.ts      (roles: [] = any auth)   [10-09]
 *   **                 — redirect to /auth/login
 *
 * Lazy loading via loadChildren (feature route files own their own RBAC guard).
 * AppShell still loaded via loadComponent.
 *
 * RBAC: rbacGuard applied inside each feature route file.
 * The RBAC_GUARD_SERVICE_TOKEN is provided by JwtService (app.config.ts 10-05).
 */
export const appRoutes: Route[] = [
  // Public auth route — no guard
  {
    path: 'auth/login',
    loadComponent: () =>
      import('./auth/login.component').then((m) => m.LoginComponent),
    title: 'Accedi — Smart Factory',
  },

  // AppShell layout route — wraps all persona areas
  {
    path: '',
    loadComponent: () =>
      import('./shell/app-shell.component').then((m) => m.AppShellComponent),
    children: [
      // Default redirect to operator (guard redirects unauthenticated to /auth/login)
      {
        path: '',
        redirectTo: 'operator',
        pathMatch: 'full',
      },

      // Operator area — role: operator (10-08)
      {
        path: 'operator',
        loadChildren: () =>
          import('./features/operator/operator.routes').then(
            (m) => m.operatorRoutes,
          ),
        title: 'Area Operatore — Smart Factory',
      },

      // Technician area — role: technician (10-09)
      {
        path: 'technician',
        loadChildren: () =>
          import('./features/technician/technician.routes').then(
            (m) => m.technicianRoutes,
          ),
        title: 'Area Tecnica — Smart Factory',
      },

      // Manager area — roles: shift-supervisor, manager (10-08)
      {
        path: 'manager',
        loadChildren: () =>
          import('./features/manager/manager.routes').then(
            (m) => m.managerRoutes,
          ),
        title: 'Area Manager — Smart Factory',
      },

      // Admin area — role: admin (10-09)
      {
        path: 'admin',
        loadChildren: () =>
          import('./features/admin/admin.routes').then(
            (m) => m.adminRoutes,
          ),
        title: 'Amministrazione — Smart Factory',
      },

      // Demo persona walkthrough — all authenticated roles (10-09)
      {
        path: 'demo',
        loadChildren: () =>
          import('./features/demo/demo.routes').then(
            (m) => m.demoRoutes,
          ),
        title: 'Demo Persona — Smart Factory',
      },
    ],
  },

  // Catch-all — redirect to login
  {
    path: '**',
    redirectTo: 'auth/login',
  },
];
