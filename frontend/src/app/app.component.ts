import {
  Component,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatButtonModule } from '@angular/material/button';
import { Subscription } from 'rxjs';

import { VoiceRecorderComponent } from './components/voice-recorder/voice-recorder.component';
import {
  ConversationComponent,
  ConversationEntry,
} from './components/conversation/conversation.component';
import { NotesListComponent } from './components/notes-list/notes-list.component';
import { CalendarViewComponent } from './components/calendar-view/calendar-view.component';
import { CostViewComponent } from './components/cost-view/cost-view.component';
import { PwaBannerComponent } from './components/pwa-banner/pwa-banner.component';
import { AudioPlayerService } from './services/audio-player.service';
import { VoiceService } from './services/voice.service';
import { WebSocketService } from './services/websocket.service';
import { AppStatus, WsResult } from './models/notebook.models';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    MatTabsModule,
    MatIconModule,
    MatSnackBarModule,
    MatButtonModule,
    VoiceRecorderComponent,
    ConversationComponent,
    NotesListComponent,
    CalendarViewComponent,
    CostViewComponent,
    PwaBannerComponent,
  ],
  template: `
    <!-- PWA: baner instalacji i aktualizacji -->
    <app-pwa-banner></app-pwa-banner>

    <div class="app-shell">
      <!-- Lewa kolumna: mikrofon + rozmowa -->
      <div class="main-panel">
        <app-voice-recorder #recorder></app-voice-recorder>

        <div class="conversation-panel">
          <div class="panel-header">
            <mat-icon>forum</mat-icon>
            <span>Rozmowa</span>
            <button
              mat-icon-button
              (click)="resetConversation()"
              matTooltip="Resetuj rozmowę"
              style="margin-left:auto"
            >
              <mat-icon>refresh</mat-icon>
            </button>
          </div>
          <app-conversation [entries]="entries"></app-conversation>
        </div>
      </div>

      <!-- Prawa kolumna: notatki + kalendarz -->
      <div class="side-panel">
        <mat-tab-group
          mat-stretch-tabs="false"
          animationDuration="200ms"
          class="side-tabs"
        >
          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>notes</mat-icon>
              <span class="tab-label">Notatki</span>
            </ng-template>
            <app-notes-list #notesList></app-notes-list>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>calendar_month</mat-icon>
              <span class="tab-label">Kalendarz</span>
            </ng-template>
            <app-calendar-view></app-calendar-view>
          </mat-tab>

          <mat-tab>
            <ng-template mat-tab-label>
              <mat-icon>payments</mat-icon>
              <span class="tab-label">Koszty</span>
            </ng-template>
            <app-cost-view></app-cost-view>
          </mat-tab>
        </mat-tab-group>
      </div>
    </div>

    <!-- Status overlay (przetwarzanie) -->
    <div class="processing-overlay" *ngIf="status === 'processing'">
      <div class="processing-inner">
        <div class="spinner-ring"></div>
        <span>{{ processingMsg }}</span>
      </div>
    </div>
  `,
  styleUrls: ['./app.component.scss'],
})
export class AppComponent implements OnInit, OnDestroy {
  @ViewChild('recorder') recorderRef!: VoiceRecorderComponent;
  @ViewChild('notesList') notesListRef!: NotesListComponent;

  entries: ConversationEntry[] = [];
  status: AppStatus = 'idle';
  processingMsg = 'Przetwarzam...';

  private subs = new Subscription();

  constructor(
    private ws: WebSocketService,
    private voice: VoiceService,
    private audioPlayer: AudioPlayerService,
    private snack: MatSnackBar
  ) {}

  ngOnInit(): void {
    this.ws.connect();

    // Aktualizuj status połączenia w komponencie rekordera
    this.subs.add(
      this.ws.isConnected$.subscribe((c) => {
        this.recorderRef?.setWsStatus(c);
        if (!c) this.snack.open('Reconnecting...', '', { duration: 2000 });
      })
    );

    // Obsługuj wiadomości z WebSocket
    this.subs.add(
      this.ws.messages.subscribe((msg) => this.handleWsMessage(msg))
    );

    // Obsługuj zdarzenia głosowe
    this.subs.add(
      this.voice.voiceEvent.subscribe(async ({ wakeWord, audioBlob }) => {
        this.setStatus('processing', 'Transkrybuję nagranie...');
        try {
          await this.ws.sendAudio(audioBlob, wakeWord);
        } catch {
          this.snack.open('Błąd wysyłania audio.', 'OK', { duration: 3000 });
          this.setStatus('idle');
        }
      })
    );
  }

  private handleWsMessage(msg: WsResult): void {
    if (msg.type === 'status') {
      this.processingMsg = msg.message ?? 'Przetwarzam...';
      return;
    }

    if (msg.type === 'error') {
      this.snack.open(msg.message ?? 'Błąd serwera', 'OK', { duration: 4000 });
      this.setStatus('idle');
      return;
    }

    if (msg.type === 'result') {
      this.entries = [
        ...this.entries,
        { timestamp: new Date(), result: msg },
      ];

      if (msg.audio) {
        this.audioPlayer.playBase64(msg.audio);
      }

      // Odśwież listę notatek po zapisie
      if (msg.intent === 'save_note' || msg.intent === 'add_calendar') {
        setTimeout(() => this.notesListRef?.loadNotes(), 500);
      }

      this.setStatus('idle');

      // Wróć do nasłuchiwania
      if (!this.voice.isCurrentlyListening) {
        this.voice.startListening();
      }
    }
  }

  resetConversation(): void {
    this.ws.resetConversation();
    this.entries = [];
  }

  setStatus(s: AppStatus, msg = 'Przetwarzam...'): void {
    this.status = s;
    this.processingMsg = msg;
    this.recorderRef?.setStatus(s);
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
    this.ws.disconnect();
  }
}
