import {
  Component,
  OnInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import {
  CATEGORY_CONFIG,
  Note,
  NoteCategory,
  NotesResponse,
} from '../../models/notebook.models';
import { NotesApiService } from '../../services/notes-api.service';

@Component({
  selector: 'app-notes-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    MatInputModule,
    MatFormFieldModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="notes-wrap">
      <!-- Wyszukiwarka RAG -->
      <div class="search-bar">
        <mat-form-field appearance="outline" class="search-field">
          <mat-label>Szukaj w notatkach (RAG)</mat-label>
          <input matInput [(ngModel)]="searchQuery" (keyup.enter)="search()" />
          <mat-icon matSuffix (click)="search()" style="cursor:pointer">search</mat-icon>
        </mat-form-field>
      </div>

      <!-- Filtry kategorii -->
      <mat-chip-set class="category-filters">
        <mat-chip
          *ngFor="let cat of categories"
          [class.active-chip]="selectedCategory === cat.key"
          (click)="selectCategory(cat.key)"
          [style.border-color]="cat.color"
        >
          <mat-icon>{{ cat.icon }}</mat-icon>
          {{ cat.label }}
          <span class="chip-count">{{ getCategoryCount(cat.key) }}</span>
        </mat-chip>
        <mat-chip
          [class.active-chip]="selectedCategory === ''"
          (click)="selectCategory('')"
        >
          <mat-icon>all_inclusive</mat-icon>
          Wszystkie
        </mat-chip>
      </mat-chip-set>

      <!-- Wyniki wyszukiwania RAG -->
      <div *ngIf="searchResults" class="search-results">
        <div class="section-header">
          <mat-icon>auto_awesome</mat-icon>
          <span>Wyniki wyszukiwania RAG: „{{ lastQuery }}"</span>
          <button mat-icon-button (click)="clearSearch()">
            <mat-icon>close</mat-icon>
          </button>
        </div>
        <pre class="rag-results">{{ searchResults }}</pre>
      </div>

      <!-- Spinner -->
      <div class="spinner-wrap" *ngIf="loading">
        <mat-spinner diameter="36"></mat-spinner>
      </div>

      <!-- Lista notatek -->
      <div *ngIf="!loading && !searchResults">
        <div *ngFor="let cat of visibleCategories" class="category-section">
          <div class="section-header">
            <mat-icon [style.color]="getCategoryColor(cat)">{{ getCategoryIcon(cat) }}</mat-icon>
            <span>{{ getCategoryLabel(cat) }}</span>
            <span class="count-badge">{{ getNotes(cat).length }}</span>
          </div>

          <div *ngIf="getNotes(cat).length === 0" class="empty-cat">
            Brak notatek
          </div>

          <mat-card
            *ngFor="let note of getNotes(cat)"
            class="note-card fade-in-up"
            [style.border-left-color]="getCategoryColor(cat)"
          >
            <mat-card-content>
              <p class="note-content">{{ note.content }}</p>
              <p *ngIf="note.enrichment" class="note-enrichment">
                <mat-icon>lightbulb</mat-icon>{{ note.enrichment }}
              </p>
              <div class="note-footer">
                <span class="note-date">{{ note.created_at | date:'d MMM, HH:mm' }}</span>
                <span class="note-id">#{{ note.id }}</span>
              </div>
            </mat-card-content>
          </mat-card>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./notes-list.component.scss'],
})
export class NotesListComponent implements OnInit {
  notes: NotesResponse | null = null;
  selectedCategory = '';
  searchQuery = '';
  searchResults: string | null = null;
  lastQuery = '';
  loading = false;

  categories = (Object.keys(CATEGORY_CONFIG) as NoteCategory[]).map((k) => ({
    key: k,
    ...CATEGORY_CONFIG[k],
  }));

  constructor(private api: NotesApiService) {}

  ngOnInit(): void {
    this.loadNotes();
  }

  loadNotes(): void {
    this.loading = true;
    this.api.getNotes(this.selectedCategory).subscribe({
      next: (data) => {
        this.notes = data;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  search(): void {
    if (!this.searchQuery.trim()) return;
    this.loading = true;
    this.lastQuery = this.searchQuery;
    this.api.searchNotes(this.searchQuery, this.selectedCategory).subscribe({
      next: (r) => {
        this.searchResults = r.results;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  clearSearch(): void {
    this.searchResults = null;
    this.searchQuery = '';
  }

  selectCategory(cat: string): void {
    this.selectedCategory = cat;
    this.clearSearch();
    this.loadNotes();
  }

  get visibleCategories(): NoteCategory[] {
    if (this.selectedCategory) return [this.selectedCategory as NoteCategory];
    return Object.keys(CATEGORY_CONFIG) as NoteCategory[];
  }

  getNotes(cat: NoteCategory): Note[] {
    return this.notes?.[cat] ?? [];
  }

  getCategoryCount(cat: string): number {
    return this.notes?.[cat as NoteCategory]?.length ?? 0;
  }

  getCategoryColor(cat: string): string {
    return CATEGORY_CONFIG[cat as NoteCategory]?.color ?? '#aaa';
  }

  getCategoryIcon(cat: string): string {
    return CATEGORY_CONFIG[cat as NoteCategory]?.icon ?? 'notes';
  }

  getCategoryLabel(cat: string): string {
    return CATEGORY_CONFIG[cat as NoteCategory]?.label ?? cat;
  }
}
