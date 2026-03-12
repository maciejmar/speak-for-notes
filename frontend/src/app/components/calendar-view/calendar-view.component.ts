import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CalendarEvent } from '../../models/notebook.models';
import { NotesApiService } from '../../services/notes-api.service';

@Component({
  selector: 'app-calendar-view',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <div class="calendar-wrap">
      <div class="cal-header">
        <mat-icon>calendar_month</mat-icon>
        <span>Kalendarz</span>
      </div>

      <div *ngIf="loading" class="spinner-wrap">
        <mat-spinner diameter="36"></mat-spinner>
      </div>

      <div *ngIf="!loading && events.length === 0" class="empty-state">
        <mat-icon>event_available</mat-icon>
        <p>Brak wydarzeń.<br>Powiedz „Notatnik, zapisz spotkanie w środę o 14:00"</p>
      </div>

      <mat-card
        *ngFor="let event of events"
        class="event-card fade-in-up"
      >
        <mat-card-content>
          <div class="event-top">
            <div class="event-date-block">
              <span class="event-day">{{ getDay(event.date) }}</span>
              <span class="event-month">{{ getMonth(event.date) }}</span>
            </div>
            <div class="event-details">
              <p class="event-title">{{ event.title }}</p>
              <p class="event-time" *ngIf="event.time">
                <mat-icon>schedule</mat-icon> {{ event.time }}
              </p>
              <p class="event-location" *ngIf="event.location">
                <mat-icon>place</mat-icon> {{ event.location }}
              </p>
              <p class="event-desc" *ngIf="event.description">{{ event.description }}</p>
            </div>
          </div>
          <div class="event-footer">
            <span>#{{ event.id }}</span>
            <span>{{ event.created_at | date:'d MMM, HH:mm' }}</span>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styleUrls: ['./calendar-view.component.scss'],
})
export class CalendarViewComponent implements OnInit {
  events: CalendarEvent[] = [];
  loading = false;

  constructor(private api: NotesApiService) {}

  ngOnInit(): void {
    this.loading = true;
    this.api.getCalendar().subscribe({
      next: (data) => {
        this.events = data;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  getDay(dateStr: string): string {
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? '?' : String(d.getDate()).padStart(2, '0');
  }

  getMonth(dateStr: string): string {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr.substring(0, 3);
    return d.toLocaleString('pl', { month: 'short' }).toUpperCase();
  }
}
