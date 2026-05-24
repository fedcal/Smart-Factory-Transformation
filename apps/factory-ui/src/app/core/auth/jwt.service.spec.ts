/**
 * Contract tests for JwtService — Plan 10-05.
 *
 * Architecture decisions (10-CONTEXT.md):
 *   - JWT stored ONLY when isPlatformBrowser() is true (SSR-safe)
 *   - HS256, dev secret from API_SECRET_KEY env, expiry 8h (one shift)
 *   - role() and isAuthenticated() are Angular Signals
 *   - logout() clears the token and resets signals
 *
 * Playwright contract (10-UI-SPEC, Step 1):
 *   page.request.post('/auth/login', ...) → token in localStorage
 */

import { TestBed } from '@angular/core/testing';
import { PLATFORM_ID } from '@angular/core';
import { JwtService, JWT_STORAGE_KEY } from './jwt.service';

// ---------------------------------------------------------------------------
// Helpers — build minimal HS256-style JWT payloads (signature not verified)
// ---------------------------------------------------------------------------

function buildJwt(
  payload: Record<string, unknown>,
  base64url = true,
): string {
  const header = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'; // { alg: HS256, typ: JWT }
  const body = base64url
    ? btoa(JSON.stringify(payload))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '')
    : btoa(JSON.stringify(payload));
  return `${header}.${body}.fakesignature`;
}

const operatorJwt = buildJwt({
  sub: 'user-1',
  email: 'operator@mantis.it',
  role: 'operator',
  exp: Math.floor(Date.now() / 1000) + 28800, // +8h
});

const supervisorJwt = buildJwt({
  sub: 'user-2',
  email: 'supervisor@mantis.it',
  role: 'shift-supervisor',
  exp: Math.floor(Date.now() / 1000) + 28800,
});

const expiredJwt = buildJwt({
  sub: 'user-1',
  email: 'operator@mantis.it',
  role: 'operator',
  exp: Math.floor(Date.now() / 1000) - 1,
});

// ---------------------------------------------------------------------------
// Token storage — isPlatformBrowser guard
// ---------------------------------------------------------------------------

describe('JwtService (browser platform)', () => {
  let service: JwtService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        JwtService,
        { provide: PLATFORM_ID, useValue: 'browser' },
      ],
    });
    service = TestBed.inject(JwtService);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('stores the token in localStorage only when running in the browser', () => {
    service.setToken(operatorJwt);
    expect(localStorage.getItem(JWT_STORAGE_KEY)).toBe(operatorJwt);
  });

  it('getToken() returns null when no token has been stored', () => {
    expect(service.getToken()).toBeNull();
  });

  // ---------------------------------------------------------------------------
  // role() signal — reflects JWT claim
  // ---------------------------------------------------------------------------

  it('role() signal returns the role claim from the stored JWT', () => {
    service.setToken(operatorJwt);
    expect(service.role()).toBe('operator');
  });

  it('role() signal returns null when no token is stored', () => {
    expect(service.role()).toBeNull();
  });

  it('role() signal updates reactively when a new token is set', () => {
    service.setToken(supervisorJwt);
    expect(service.role()).toBe('shift-supervisor');
  });

  // ---------------------------------------------------------------------------
  // isAuthenticated() signal
  // ---------------------------------------------------------------------------

  it('isAuthenticated() returns true when a non-expired token is stored', () => {
    service.setToken(operatorJwt);
    expect(service.isAuthenticated()).toBe(true);
  });

  it('isAuthenticated() returns false when no token is stored', () => {
    expect(service.isAuthenticated()).toBe(false);
  });

  it('isAuthenticated() returns false when the stored token is expired', () => {
    service.setToken(expiredJwt);
    expect(service.isAuthenticated()).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // logout() — clears token and resets signals
  // ---------------------------------------------------------------------------

  it('logout() removes the token from localStorage and resets role() to null', () => {
    service.setToken(operatorJwt);
    service.logout();
    expect(service.getToken()).toBeNull();
    expect(service.role()).toBeNull();
    expect(service.isAuthenticated()).toBe(false);
  });

  it('logout() removes token from localStorage', () => {
    service.setToken(operatorJwt);
    service.logout();
    expect(localStorage.getItem(JWT_STORAGE_KEY)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// SSR platform — localStorage must NOT be touched
// ---------------------------------------------------------------------------

describe('JwtService (server platform)', () => {
  let service: JwtService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        JwtService,
        { provide: PLATFORM_ID, useValue: 'server' },
      ],
    });
    service = TestBed.inject(JwtService);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('does NOT write to localStorage on server platform (SSR guard)', () => {
    service.setToken('fake.jwt.token');
    // localStorage should remain untouched on server
    expect(localStorage.getItem(JWT_STORAGE_KEY)).toBeNull();
  });

  it('getToken() still returns the token set in memory on server', () => {
    service.setToken('fake.jwt.token');
    // Token is still in memory (signal) even on server
    expect(service.getToken()).toBe('fake.jwt.token');
  });
});
