/**
 * Contract tests for LoginComponent — CR-04 fix verification.
 *
 * Verifies that after a successful login SseService.connect() is called with
 * the correct /v1/stream/kpi endpoint, NOT the non-existent /v1/stream/events.
 *
 * Plan: 10-03, 10-UI-SPEC Component 2 — CR-04 fix.
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PLATFORM_ID } from '@angular/core';
import { MatSnackBarModule } from '@angular/material/snack-bar';

import { LoginComponent } from './login.component';
import { JwtService } from '../core/auth/jwt.service';
import { SseService } from '../core/sse/sse.service';
import { RBAC_GUARD_SERVICE_TOKEN } from '../core/auth/rbac.guard';

// ---------------------------------------------------------------------------
// Helpers — minimal valid JWT (8h from now)
// ---------------------------------------------------------------------------

function buildFakeJwt(role: string): string {
  const payload = btoa(
    JSON.stringify({
      sub: `${role}@mantis.it`,
      email: `${role}@mantis.it`,
      role,
      exp: Math.floor(Date.now() / 1000) + 28800,
    }),
  )
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
  return `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${payload}.fakesig`;
}

describe('LoginComponent — CR-04: correct SSE URL after login', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let component: LoginComponent;
  let httpController: HttpTestingController;
  let sseConnectSpy: jest.Mock;
  let navigateSpy: jest.Mock;

  beforeEach(async () => {
    sseConnectSpy = jest.fn();
    navigateSpy = jest.fn();

    await TestBed.configureTestingModule({
      imports: [
        NoopAnimationsModule,
        HttpClientTestingModule,
        ReactiveFormsModule,
        LoginComponent,
      ],
      providers: [
        { provide: PLATFORM_ID, useValue: 'browser' },
        {
          provide: Router,
          useValue: { navigate: navigateSpy },
        },
        {
          provide: SseService,
          useValue: { connect: sseConnectSpy },
        },
        {
          provide: RBAC_GUARD_SERVICE_TOKEN,
          useValue: {
            isAuthenticated: () => false,
            getCurrentRole: () => null,
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpController.verify();
    TestBed.resetTestingModule();
  });

  it('calls SseService.connect with /v1/stream/kpi (not the non-existent /v1/stream/events)', () => {
    // Fill the form and submit
    component.loginForm.setValue({
      email: 'operator@mantis.it',
      password: 'mantis2026',
    });
    component.onSubmit();

    // Respond with a fake token
    const req = httpController.expectOne('/auth/login');
    req.flush({
      access_token: buildFakeJwt('operator'),
      token_type: 'bearer',
    });

    expect(sseConnectSpy).toHaveBeenCalledTimes(1);
    const [calledUrl] = sseConnectSpy.mock.calls[0] as [string, string];

    // CR-04: must use /v1/stream/kpi, not /v1/stream/events
    expect(calledUrl).toBe('/v1/stream/kpi');
    expect(calledUrl).not.toContain('/v1/stream/events');
  });

  it('does NOT connect to /v1/stream/events at any point', () => {
    component.loginForm.setValue({
      email: 'operator@mantis.it',
      password: 'mantis2026',
    });
    component.onSubmit();

    const req = httpController.expectOne('/auth/login');
    req.flush({
      access_token: buildFakeJwt('operator'),
      token_type: 'bearer',
    });

    const allUrls = sseConnectSpy.mock.calls.map((c: [string, string]) => c[0]);
    expect(allUrls.some((u: string) => u.includes('/v1/stream/events'))).toBe(false);
  });
});
