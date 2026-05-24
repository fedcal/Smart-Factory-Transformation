import {
  inject,
  Injectable,
  PLATFORM_ID,
  signal,
  computed,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { UserRole } from './rbac.guard';

/**
 * Decoded JWT payload structure.
 * Sub-set of JWT standard claims + SFT custom role claim.
 */
export interface JwtPayload {
  sub: string;
  email: string;
  role: UserRole;
  exp: number;
}

/**
 * localStorage key for the JWT token.
 * Must match the key read by Playwright E2E (10-UI-SPEC Step 1).
 */
export const JWT_STORAGE_KEY = 'sft_token';

/**
 * JwtService — browser-safe token storage + Angular Signals for auth state.
 *
 * SSR guard: ALL localStorage access is behind isPlatformBrowser() (T-10-05-01).
 * Signals: role() and isAuthenticated() are computed() from _token signal.
 * Client-side exp check is advisory only — server validates signature on every
 * request (T-10-05-04).
 */
@Injectable({ providedIn: 'root' })
export class JwtService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  /** Raw JWT string signal. null when not authenticated. */
  private readonly _token = signal<string | null>(this._readFromStorage());

  /** Decoded payload or null. Recomputed when _token changes. */
  private readonly _payload = computed<JwtPayload | null>(() => {
    const raw = this._token();
    if (!raw) return null;
    return decodeJwtPayload(raw);
  });

  /**
   * Current user role from the JWT claim.
   * Returns null when no valid token is present.
   */
  readonly role = computed<UserRole | null>(() => {
    const payload = this._payload();
    return payload?.role ?? null;
  });

  /**
   * True when a non-expired token is present.
   * Expiry is checked client-side as advisory only (server is authoritative).
   */
  readonly isAuthenticated = computed<boolean>(() => {
    const payload = this._payload();
    if (!payload) return false;
    const nowSeconds = Math.floor(Date.now() / 1000);
    return payload.exp > nowSeconds;
  });

  /**
   * Returns the raw JWT string, or null when not authenticated.
   * Never touches localStorage directly — reads the signal.
   */
  getToken(): string | null {
    return this._token();
  }

  /**
   * Stores the JWT in localStorage (browser only) and updates the signal.
   * No-op on server platform — SSR guard (T-10-05-01).
   */
  setToken(token: string): void {
    if (this.isBrowser) {
      localStorage.setItem(JWT_STORAGE_KEY, token);
    }
    this._token.set(token);
  }

  /**
   * Returns the current user role — alias for the role signal value.
   * Required by RBAC_GUARD_SERVICE_TOKEN interface (10-04 boundary contract).
   */
  getCurrentRole(): UserRole | null {
    return this.role();
  }

  /**
   * Clears the JWT from storage and resets all auth signals.
   */
  logout(): void {
    if (this.isBrowser) {
      localStorage.removeItem(JWT_STORAGE_KEY);
    }
    this._token.set(null);
  }

  /**
   * Reads the stored token from localStorage on service initialisation.
   * Returns null on server platform (SSR guard).
   *
   * WR-01: uses this.isBrowser (already computed from platformId) instead of
   * calling inject(PLATFORM_ID) a second time. The double inject was fragile —
   * if _readFromStorage were called outside a DI construction context it would
   * throw. The field initialiser order in Angular guarantees that platformId
   * and isBrowser are set before _token's initialiser runs.
   */
  private _readFromStorage(): string | null {
    if (!this.isBrowser) {
      return null;
    }
    return localStorage.getItem(JWT_STORAGE_KEY);
  }
}

/**
 * Decodes the payload of a JWT without verifying the signature.
 * Verification is the server's responsibility; this is advisory-only (T-10-05-04).
 *
 * Returns null on any decoding error (malformed base64, invalid JSON, etc.).
 */
function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payloadB64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const jsonStr = atob(payloadB64);
    const parsed = JSON.parse(jsonStr) as Partial<JwtPayload>;

    if (
      typeof parsed.sub !== 'string' ||
      typeof parsed.role !== 'string' ||
      typeof parsed.exp !== 'number'
    ) {
      return null;
    }

    return parsed as JwtPayload;
  } catch {
    return null;
  }
}
