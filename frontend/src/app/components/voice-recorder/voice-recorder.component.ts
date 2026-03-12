import {
  Component,
  EventEmitter,
  OnDestroy,
  OnInit,
  Output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subscription } from 'rxjs';
import { AppStatus } from '../../models/notebook.models';
import { VoiceService } from '../../services/voice.service';

@Component({
  selector: 'app-voice-recorder',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, MatTooltipModule],
  template: `
    <div class="recorder-wrap">
      <!-- Ikona tytułu -->
      <div class="app-title">
        <mat-icon class="title-icon">mic_none</mat-icon>
        <span>Notatnik Głosowy</span>
      </div>

      <!-- Centralny przycisk mikrofonu -->
      <div class="mic-container" [class.active]="isListening" [class.recording]="isRecording">
        <!-- Animowane pierścienie -->
        <div class="ring ring-1" *ngIf="isListening || isRecording"></div>
        <div class="ring ring-2" *ngIf="isListening || isRecording"></div>

        <button
          mat-fab
          class="mic-btn"
          [class.listening]="isListening && !isRecording"
          [class.recording]="isRecording"
          [class.processing]="status === 'processing'"
          (click)="toggleListening()"
          [matTooltip]="isListening ? 'Zatrzymaj nasłuchiwanie' : 'Aktywuj nasłuchiwanie'"
        >
          <mat-icon>{{ micIcon }}</mat-icon>
        </button>
      </div>

      <!-- Fale audio (widoczne podczas nagrywania) -->
      <div class="audio-waves" *ngIf="isRecording">
        <div class="wave" *ngFor="let i of [1,2,3,4,5,6,7]" [style.animation-delay]="(i * 0.1) + 's'"></div>
      </div>

      <!-- Komunikat statusu -->
      <p class="status-text" [class.recording-text]="isRecording">{{ statusMessage }}</p>

      <!-- Hasła aktywujące -->
      <div class="wake-words" *ngIf="!isListening">
        <div class="wake-word-chip">
          <mat-icon>save</mat-icon>
          <span>„Notatnik, zapisz"</span>
        </div>
        <div class="wake-word-chip">
          <mat-icon>chat</mat-icon>
          <span>„Notatnik, powiedz"</span>
        </div>
      </div>

      <!-- Przycisk zatrzymania nagrywania -->
      <button
        *ngIf="isRecording"
        mat-stroked-button
        class="stop-btn"
        (click)="stopRecording()"
      >
        <mat-icon>stop</mat-icon> Zatrzymaj nagrywanie
      </button>

      <!-- Wskaźnik połączenia WS -->
      <div class="connection-indicator" [class.connected]="wsConnected">
        <span class="dot"></span>
        <span class="label">{{ wsConnected ? 'Połączono' : 'Łączę...' }}</span>
      </div>
    </div>
  `,
  styleUrls: ['./voice-recorder.component.scss'],
})
export class VoiceRecorderComponent implements OnInit, OnDestroy {
  @Output() connected = new EventEmitter<boolean>();

  isListening = false;
  isRecording = false;
  statusMessage = 'Naciśnij mikrofon, aby aktywować';
  wsConnected = false;
  status: AppStatus = 'idle';

  private subs = new Subscription();

  constructor(private voice: VoiceService) {}

  ngOnInit(): void {
    this.subs.add(
      this.voice.isListening.subscribe((v) => (this.isListening = v))
    );
    this.subs.add(
      this.voice.isRecording.subscribe((v) => (this.isRecording = v))
    );
    this.subs.add(
      this.voice.statusMessage.subscribe((v) => (this.statusMessage = v))
    );
  }

  get micIcon(): string {
    if (this.isRecording) return 'fiber_manual_record';
    if (this.isListening) return 'mic';
    return 'mic_off';
  }

  toggleListening(): void {
    if (this.isListening) {
      this.voice.stopListening();
    } else {
      this.voice.startListening();
    }
  }

  stopRecording(): void {
    this.voice.stopRecording();
  }

  setWsStatus(connected: boolean): void {
    this.wsConnected = connected;
  }

  setStatus(status: AppStatus): void {
    this.status = status;
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }
}
