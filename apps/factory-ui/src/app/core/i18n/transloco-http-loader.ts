import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Translation, TranslocoLoader } from '@jsverse/transloco';
import { Observable } from 'rxjs';

/**
 * HTTP loader for transloco — reads translation files from assets/i18n/{lang}.json.
 *
 * Used in app.config.ts via provideTransloco({ loader: TranslocoHttpLoader }).
 * SSR: the Angular HTTP client works on both server and browser (with TransferState).
 */
@Injectable({ providedIn: 'root' })
export class TranslocoHttpLoader implements TranslocoLoader {
  private readonly http = inject(HttpClient);

  getTranslation(lang: string): Observable<Translation> {
    return this.http.get<Translation>(`/assets/i18n/${lang}.json`);
  }
}
