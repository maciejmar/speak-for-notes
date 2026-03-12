import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { PwaService } from '../../services/pwa.service';

@Component({
  selector: 'app-pwa-banner',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatSnackBarModule],
  template: `
    <!-- Baner "Zainstaluj aplikację" -->
    <div class="install-banner" *ngIf="showInstall" role="banner">
      <div class="banner-content">
        <img src="assets/icons/icon.svg" alt="ikona" class="banner-icon">
        <div class="banner-text">
          <strong>Zainstaluj Notatnik</strong>
          <span>Działa offline i na ekranie głównym</span>
        </div>
      </div>
      <div class="banner-actions">
        <button mat-button class="install-btn" (click)="install()">
          <mat-icon>download</mat-icon> Zainstaluj
        </button>
        <button mat-icon-button class="dismiss-btn" (click)="dismiss()" aria-label="Zamknij">
          <mat-icon>close</mat-icon>
        </button>
      </div>
    </div>

    <!-- Baner "Dostępna aktualizacja" -->
    <div class="update-banner" *ngIf="showUpdate" role="banner">
      <div class="banner-content">
        <mat-icon class="update-icon">system_update</mat-icon>
        <span>Dostępna nowa wersja aplikacji</span>
      </div>
      <button mat-button class="update-btn" (click)="applyUpdate()">
        Aktualizuj
      </button>
    </div>
  `,
  styles: [`
    /* ── Baner instalacji ── */
    .install-banner {
      position: fixed;
      bottom: 0; left: 0; right: 0;
      background: linear-gradient(135deg, #1e1e3f, #2d2d5e);
      border-top: 1px solid rgba(124, 124, 255, 0.3);
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      z-index: 2000;
      animation: slideUp 0.3s ease-out;
      /* Safe area dla notch/home indicator */
      padding-bottom: max(12px, env(safe-area-inset-bottom));
    }

    .banner-content {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;
      min-width: 0;
    }

    .banner-icon {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      flex-shrink: 0;
    }

    .banner-text {
      display: flex;
      flex-direction: column;
      min-width: 0;

      strong {
        font-size: 0.9rem;
        color: #e0e0f0;
        white-space: nowrap;
      }

      span {
        font-size: 0.75rem;
        color: #9090b8;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    .banner-actions {
      display: flex;
      align-items: center;
      gap: 4px;
      flex-shrink: 0;
    }

    .install-btn {
      color: #7c7cff !important;
      font-weight: 600 !important;
    }

    .dismiss-btn {
      color: #555580 !important;
    }

    /* ── Baner aktualizacji ── */
    .update-banner {
      position: fixed;
      top: 0; left: 0; right: 0;
      background: linear-gradient(135deg, #1e3a1e, #2d5e2d);
      border-bottom: 1px solid rgba(82, 183, 136, 0.4);
      padding: 10px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      z-index: 2000;
      animation: slideDown 0.3s ease-out;
      padding-top: max(10px, env(safe-area-inset-top));
    }

    .update-icon {
      color: #52b788;
    }

    .update-btn {
      color: #52b788 !important;
      font-weight: 600 !important;
      white-space: nowrap;
    }

    @keyframes slideUp {
      from { transform: translateY(100%); }
      to   { transform: translateY(0); }
    }

    @keyframes slideDown {
      from { transform: translateY(-100%); }
      to   { transform: translateY(0); }
    }
  `],
})
export class PwaBannerComponent implements OnInit {
  showInstall = false;
  showUpdate = false;

  constructor(
    private pwa: PwaService,
    private snack: MatSnackBar
  ) {}

  ngOnInit(): void {
    // Nie pokazuj banera instalacji jeśli już zainstalowana
    this.pwa.canInstall$.subscribe((can) => {
      this.showInstall = can && !this.pwa.isInstalled$.value;
    });

    this.pwa.updateAvailable$.subscribe((available) => {
      this.showUpdate = available;
    });
  }

  async install(): Promise<void> {
    const outcome = await this.pwa.install();
    if (outcome === 'accepted') {
      this.snack.open('Aplikacja zainstalowana!', '', { duration: 3000 });
    }
    this.showInstall = false;
  }

  dismiss(): void {
    this.showInstall = false;
  }

  applyUpdate(): void {
    this.pwa.applyUpdate();
  }
}
