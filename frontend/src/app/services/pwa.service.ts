import { ApplicationRef, Injectable, OnDestroy } from '@angular/core';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { BehaviorSubject, Subscription, concat, first, interval } from 'rxjs';
import { filter } from 'rxjs/operators';

// Typ dla zdarzenia beforeinstallprompt (nie ma w standardowych typach)
interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  readonly userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

@Injectable({ providedIn: 'root' })
export class PwaService implements OnDestroy {
  private deferredPrompt: BeforeInstallPromptEvent | null = null;
  private subs = new Subscription();

  readonly canInstall$ = new BehaviorSubject<boolean>(false);
  readonly updateAvailable$ = new BehaviorSubject<boolean>(false);
  readonly isInstalled$ = new BehaviorSubject<boolean>(false);

  constructor(
    private swUpdate: SwUpdate,
    private appRef: ApplicationRef
  ) {
    this._detectInstalled();
    this._listenInstallPrompt();
    if (this.swUpdate.isEnabled) {
      this._setupUpdateCheck();
    }
  }

  // ── Install ──────────────────────────────────────────────────────────────

  async install(): Promise<'accepted' | 'dismissed' | 'unavailable'> {
    if (!this.deferredPrompt) return 'unavailable';

    await this.deferredPrompt.prompt();
    const { outcome } = await this.deferredPrompt.userChoice;
    this.deferredPrompt = null;
    this.canInstall$.next(false);
    return outcome;
  }

  // ── Update ───────────────────────────────────────────────────────────────

  async applyUpdate(): Promise<void> {
    await this.swUpdate.activateUpdate();
    document.location.reload();
  }

  // ── Private ──────────────────────────────────────────────────────────────

  private _detectInstalled(): void {
    // Sprawdź czy aplikacja działa w trybie standalone (zainstalowana)
    const isStandalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true;

    this.isInstalled$.next(isStandalone);

    // Nasłuchuj zmiany trybu wyświetlania
    window.matchMedia('(display-mode: standalone)').addEventListener(
      'change',
      (e) => this.isInstalled$.next(e.matches)
    );
  }

  private _listenInstallPrompt(): void {
    window.addEventListener('beforeinstallprompt', (e: Event) => {
      e.preventDefault();
      this.deferredPrompt = e as BeforeInstallPromptEvent;
      this.canInstall$.next(true);
    });

    window.addEventListener('appinstalled', () => {
      this.deferredPrompt = null;
      this.canInstall$.next(false);
      this.isInstalled$.next(true);
    });
  }

  private _setupUpdateCheck(): void {
    // Sprawdzaj aktualizacje co 6 godzin po stabilizacji aplikacji
    const appIsStable$ = this.appRef.isStable.pipe(first((stable) => stable));
    const every6h$ = interval(6 * 60 * 60 * 1000);
    const checkWhenStable$ = concat(appIsStable$, every6h$);

    this.subs.add(
      checkWhenStable$.subscribe(() => this.swUpdate.checkForUpdate())
    );

    // Powiadom o dostępnej aktualizacji
    this.subs.add(
      this.swUpdate.versionUpdates
        .pipe(filter((e): e is VersionReadyEvent => e.type === 'VERSION_READY'))
        .subscribe(() => this.updateAvailable$.next(true))
    );
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }
}
