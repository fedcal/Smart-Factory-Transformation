import {
  ApplicationConfig,
  provideZoneChangeDetection,
  APP_INITIALIZER,
  inject,
  PLATFORM_ID,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { appRoutes } from './app.routes';
import {
  provideClientHydration,
  withEventReplay,
} from '@angular/platform-browser';
import { provideAnimations } from '@angular/platform-browser/animations';
import {
  provideHttpClient,
  withInterceptors,
  withFetch,
} from '@angular/common/http';
import { isPlatformBrowser } from '@angular/common';
import { provideTransloco } from '@jsverse/transloco';
import { TranslocoHttpLoader } from './core/i18n/transloco-http-loader';
import { JwtService } from './core/auth/jwt.service';
import { ThemeService } from './core/theme/theme.service';
import { LocaleService } from './core/i18n/locale.service';
import { jwtInterceptor } from './core/auth/jwt.interceptor';
import { RBAC_GUARD_SERVICE_TOKEN } from './core/auth/rbac.guard';

/**
 * APP_INITIALIZER that restores the persisted locale + theme on browser startup.
 *
 * SSR: both services are SSR-safe and default to 'it' / 'dark' on the server.
 * Browser: reads localStorage on first hydration and applies saved preferences.
 */
function initializePlatform(): () => void {
  const platformId = inject(PLATFORM_ID);
  const themeService = inject(ThemeService);
  const localeService = inject(LocaleService);

  return () => {
    if (!isPlatformBrowser(platformId)) return;

    // ThemeService already reads localStorage in its constructor (signal init).
    // We call setTheme() to ensure the data-theme attribute is applied on the
    // browser side (after SSR hydration the DOM attribute may need re-application).
    themeService.setTheme(themeService.theme());

    // LocaleService: switch to the stored locale (triggers transloco load).
    const storedLocale = localeService.locale();
    if (storedLocale !== 'it') {
      localeService.switchLang(storedLocale);
    }
  };
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideClientHydration(withEventReplay()),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(appRoutes),
    provideAnimations(),

    // HTTP client with JWT interceptor (functional interceptor)
    provideHttpClient(
      withFetch(),
      withInterceptors([jwtInterceptor]),
    ),

    // Transloco — runtime i18n IT/EN, lazy HTTP loader (UI-07)
    provideTransloco({
      config: {
        availableLangs: ['it', 'en'],
        defaultLang: 'it',
        reRenderOnLangChange: true,
        prodMode: false,
        missingHandler: {
          useFallbackTranslation: true,
          logMissingKey: true,
        },
      },
      loader: TranslocoHttpLoader,
    }),

    // RBAC guard service token — provides JwtService as the guard dependency
    // (boundary established in 10-04; this is the 10-05 implementation)
    {
      provide: RBAC_GUARD_SERVICE_TOKEN,
      useExisting: JwtService,
    },

    // Platform initializer — restores theme + locale on browser hydration
    {
      provide: APP_INITIALIZER,
      useFactory: initializePlatform,
      multi: true,
    },
  ],
};
