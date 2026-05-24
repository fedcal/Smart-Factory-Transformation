import { Route } from '@angular/router';
import { rbacGuard, UserRole } from './core/auth/rbac.guard';

/**
 * Application route map — Phase 10-04
 *
 * Structure:
 *   /auth/login        — public login page
 *   /                  — AppShell layout route (RBAC guard on each child)
 *     /operator        — operator persona (roles: operator)
 *     /technician      — technician persona (roles: technician)
 *     /manager         — manager/supervisor persona (roles: shift-supervisor, manager)
 *     /admin           — admin area (roles: admin)
 *     /demo            — persona walkthrough demo (all authenticated roles)
 *   **                 — redirect to /auth/login
 *
 * Lazy loading:
 *   - AppShell loaded lazily via loadComponent
 *   - Feature areas loaded via loadComponent (10-07 replaces placeholders)
 *   - Login loaded lazily
 *
 * RBAC guard: rbacGuard (scaffold in 10-04, real implementation in 10-05).
 * Roles data key: 'roles' — [] means any authenticated user.
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
      // Default redirect to login when unauthenticated (guard handles it)
      {
        path: '',
        redirectTo: 'operator',
        pathMatch: 'full',
      },

      // Operator area — role: operator (plan 10-08: wired to real OperatorComponent)
      {
        path: 'operator',
        loadChildren: () =>
          import('./features/operator/operator.routes').then(
            (m) => m.operatorRoutes,
          ),
        title: 'Area Operatore — Smart Factory',
      },

      // Technician area — role: technician
      {
        path: 'technician',
        loadComponent: () =>
          import('./features/technician/technician.component').then(
            (m) => m.TechnicianComponent,
          ),
        canActivate: [rbacGuard],
        data: { roles: ['technician'] as UserRole[] },
        title: 'Area Tecnica — Smart Factory',
      },

      // Manager area — roles: shift-supervisor, manager (plan 10-08: wired to real ManagerComponent)
      {
        path: 'manager',
        loadChildren: () =>
          import('./features/manager/manager.routes').then(
            (m) => m.managerRoutes,
          ),
        title: 'Area Manager — Smart Factory',
      },

      // Admin area — role: admin
      {
        path: 'admin',
        loadComponent: () =>
          import('./features/admin/admin.component').then(
            (m) => m.AdminComponent,
          ),
        canActivate: [rbacGuard],
        data: { roles: ['admin'] as UserRole[] },
        title: 'Amministrazione — Smart Factory',
      },

      // Demo persona walkthrough — all authenticated roles (empty roles array = any)
      {
        path: 'demo',
        loadComponent: () =>
          import('./features/demo/demo.component').then(
            (m) => m.DemoComponent,
          ),
        canActivate: [rbacGuard],
        data: { roles: [] as UserRole[] },
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
