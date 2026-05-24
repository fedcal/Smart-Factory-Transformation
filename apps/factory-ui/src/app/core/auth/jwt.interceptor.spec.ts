/**
 * Contract tests for jwtInterceptor — WR-06 fix verification.
 *
 * Verifies that the Bearer token is attached ONLY to same-origin or relative
 * API URLs and is NEVER sent to absolute external hosts.
 *
 * Plan: 10-05 — WR-06 fix.
 */

import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  HttpRequest,
  HttpHandler,
  HttpResponse,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { PLATFORM_ID } from '@angular/core';
import { of } from 'rxjs';

import { jwtInterceptor } from './jwt.interceptor';
import { JwtService } from './jwt.service';

// ---------------------------------------------------------------------------
// Helpers — build a minimal valid JWT (8h)
// ---------------------------------------------------------------------------

function buildFakeJwt(): string {
  const payload = btoa(
    JSON.stringify({
      sub: 'op@mantis.it',
      email: 'op@mantis.it',
      role: 'operator',
      exp: Math.floor(Date.now() / 1000) + 28800,
    }),
  )
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '');
  return `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.${payload}.fakesig`;
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

describe('jwtInterceptor — WR-06: same-origin Bearer token guard', () => {
  let http: HttpClient;
  let httpController: HttpTestingController;
  let jwtService: JwtService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        { provide: PLATFORM_ID, useValue: 'browser' },
        provideHttpClient(withInterceptors([jwtInterceptor])),
        provideHttpClientTesting(),
        JwtService,
      ],
    });

    http = TestBed.inject(HttpClient);
    httpController = TestBed.inject(HttpTestingController);
    jwtService = TestBed.inject(JwtService);
    jwtService.setToken(buildFakeJwt());
  });

  afterEach(() => {
    httpController.verify();
    TestBed.resetTestingModule();
  });

  // ---------------------------------------------------------------------------
  // Relative URLs — must attach Bearer
  // ---------------------------------------------------------------------------

  it('attaches Bearer token to a relative /v1/ URL', () => {
    http.get('/v1/kpi').subscribe();

    const req = httpController.expectOne('/v1/kpi');
    expect(req.request.headers.has('Authorization')).toBe(true);
    expect(req.request.headers.get('Authorization')).toMatch(/^Bearer /);
    req.flush({});
  });

  it('attaches Bearer token to /auth/me (relative)', () => {
    http.get('/auth/me').subscribe();

    const req = httpController.expectOne('/auth/me');
    expect(req.request.headers.has('Authorization')).toBe(true);
    req.flush({});
  });

  // ---------------------------------------------------------------------------
  // External absolute URLs — must NOT attach Bearer
  // ---------------------------------------------------------------------------

  it('does NOT attach Bearer token to an absolute external URL containing /v1/', () => {
    http.get('https://evil.example.com/v1/kpi').subscribe();

    const req = httpController.expectOne('https://evil.example.com/v1/kpi');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('does NOT attach Bearer token to an absolute external URL matching /auth/me', () => {
    http.get('https://external.api.com/auth/me').subscribe();

    const req = httpController.expectOne('https://external.api.com/auth/me');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  // ---------------------------------------------------------------------------
  // Non-API relative URLs — must NOT attach Bearer
  // ---------------------------------------------------------------------------

  it('does NOT attach Bearer token to a relative URL not matching API patterns', () => {
    http.get('/public/info').subscribe();

    const req = httpController.expectOne('/public/info');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('does NOT attach Bearer token to /auth/login', () => {
    http.post('/auth/login', {}).subscribe();

    const req = httpController.expectOne('/auth/login');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({ access_token: 'x', token_type: 'bearer' });
  });
});
