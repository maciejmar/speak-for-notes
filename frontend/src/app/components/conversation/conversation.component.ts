import {
  Component,
  ElementRef,
  Input,
  OnChanges,
  ViewChild,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { CATEGORY_CONFIG, WsResult } from '../../models/notebook.models';

export interface ConversationEntry {
  timestamp: Date;
  result: WsResult;
  userText?: string;
}

@Component({
  selector: 'app-conversation',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatChipsModule],
  template: `
    <div class="conv-wrap" #scrollContainer>
      <div *ngIf="entries.length === 0" class="empty-state">
        <mat-icon>forum</mat-icon>
        <p>Brak rozmów. Zacznij od powiedzenia hasła aktywującego.</p>
      </div>

      <div
        *ngFor="let entry of entries; trackBy: trackByTime"
        class="entry fade-in-up"
      >
        <!-- Użytkownik -->
        <div class="bubble user-bubble" *ngIf="entry.result.transcription">
          <mat-icon class="bubble-icon">person</mat-icon>
          <div class="bubble-content">
            <span class="bubble-text">{{ entry.result.transcription }}</span>
            <span class="bubble-time">{{ entry.timestamp | date:'HH:mm' }}</span>
          </div>
        </div>

        <!-- Odpowiedź asystenta -->
        <div class="bubble assistant-bubble" *ngIf="entry.result.response_text">
          <mat-icon class="bubble-icon">smart_toy</mat-icon>
          <div class="bubble-content">
            <span class="bubble-text">{{ entry.result.response_text }}</span>

            <!-- Metadane notatki -->
            <div class="note-meta" *ngIf="entry.result.intent === 'save_note' && entry.result.category">
              <mat-chip class="category-chip"
                [style.background-color]="getCategoryColor(entry.result.category) + '22'"
                [style.color]="getCategoryColor(entry.result.category)"
              >
                <mat-icon>{{ getCategoryIcon(entry.result.category) }}</mat-icon>
                {{ getCategoryLabel(entry.result.category) }}
              </mat-chip>
              <span *ngIf="entry.result.saved_id" class="note-id">#{{ entry.result.saved_id }}</span>
            </div>

            <!-- Wzbogacenie (research) -->
            <div class="enrichment" *ngIf="entry.result.enrichment">
              <mat-icon>search</mat-icon>
              <span>{{ entry.result.enrichment }}</span>
            </div>
          </div>
        </div>

        <!-- Błąd -->
        <div class="bubble error-bubble" *ngIf="entry.result.error">
          <mat-icon>error_outline</mat-icon>
          <span>{{ entry.result.error }}</span>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./conversation.component.scss'],
})
export class ConversationComponent implements OnChanges {
  @Input() entries: ConversationEntry[] = [];
  @ViewChild('scrollContainer') private scrollRef!: ElementRef<HTMLDivElement>;

  readonly CATEGORY_CONFIG = CATEGORY_CONFIG;

  trackByTime(_: number, e: ConversationEntry): number {
    return e.timestamp.getTime();
  }

  ngOnChanges(): void {
    setTimeout(() => this.scrollToBottom(), 50);
  }

  getCategoryColor(cat: string): string {
    return (CATEGORY_CONFIG as Record<string, { color: string }>)[cat]?.color ?? '#aaa';
  }

  getCategoryIcon(cat: string): string {
    return (CATEGORY_CONFIG as Record<string, { icon: string }>)[cat]?.icon ?? 'notes';
  }

  getCategoryLabel(cat: string): string {
    return (CATEGORY_CONFIG as Record<string, { label: string }>)[cat]?.label ?? cat;
  }

  private scrollToBottom(): void {
    if (this.scrollRef) {
      const el = this.scrollRef.nativeElement;
      el.scrollTop = el.scrollHeight;
    }
  }
}
