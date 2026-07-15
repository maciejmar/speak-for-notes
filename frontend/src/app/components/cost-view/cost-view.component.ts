import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { CostSummary } from '../../models/notebook.models';
import { NotesApiService } from '../../services/notes-api.service';

const AGENT_LABELS: Record<string, string> = {
  intent: 'Klasyfikacja intencji',
  categorization: 'Kategoryzacja',
  research: 'Badanie tematu',
  response: 'Generowanie odpowiedzi',
};

@Component({
  selector: 'app-cost-view',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule],
  template: `
    <div class="cost-wrap">
      <div class="cost-header">
        <mat-icon>payments</mat-icon>
        <span>Koszty LLM zewnętrznego</span>
      </div>

      <div *ngIf="loading" class="spinner-wrap">
        <mat-spinner diameter="36"></mat-spinner>
      </div>

      <ng-container *ngIf="!loading && summary as s">
        <div *ngIf="s.total_calls === 0" class="empty-state">
          <mat-icon>check_circle</mat-icon>
          <p>Brak kosztów. Lokalna Ollama obsługuje wszystko sama —<br>fallback na {{ s.model }} jeszcze nie był potrzebny.</p>
        </div>

        <ng-container *ngIf="s.total_calls > 0">
          <mat-card class="total-card">
            <mat-card-content>
              <div class="total-amount">{{ s.total_cost_usd | number:'1.4-6' }} USD</div>
              <div class="total-sub">
                {{ s.total_calls }} wywołań fallbacku ({{ s.model }}) ·
                {{ s.total_input_tokens }} tok. wej. / {{ s.total_output_tokens }} tok. wyj.
              </div>
            </mat-card-content>
          </mat-card>

          <div class="section-label">Wg agenta</div>
          <mat-card *ngFor="let entry of agentEntries" class="agent-card">
            <mat-card-content>
              <div class="agent-row">
                <span class="agent-name">{{ agentLabel(entry[0]) }}</span>
                <span class="agent-cost">{{ entry[1].cost_usd | number:'1.4-6' }} USD</span>
              </div>
              <div class="agent-calls">{{ entry[1].calls }} wywołań</div>
            </mat-card-content>
          </mat-card>

          <div class="section-label">Ostatnie wywołania</div>
          <mat-card *ngFor="let e of s.recent" class="recent-card">
            <mat-card-content>
              <div class="recent-row">
                <span class="recent-agent">{{ agentLabel(e.agent) }}</span>
                <span class="recent-cost">{{ e.cost_usd | number:'1.4-6' }} USD</span>
              </div>
              <div class="recent-meta">
                {{ e.timestamp | date:'d MMM, HH:mm:ss' }} ·
                {{ e.input_tokens }}/{{ e.output_tokens }} tok.
              </div>
            </mat-card-content>
          </mat-card>
        </ng-container>
      </ng-container>
    </div>
  `,
  styleUrls: ['./cost-view.component.scss'],
})
export class CostViewComponent implements OnInit {
  summary: CostSummary | null = null;
  loading = false;

  constructor(private api: NotesApiService) {}

  ngOnInit(): void {
    this.loadCosts();
  }

  loadCosts(): void {
    this.loading = true;
    this.api.getCosts().subscribe({
      next: (data) => {
        this.summary = data;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  get agentEntries() {
    return this.summary ? Object.entries(this.summary.by_agent) : [];
  }

  agentLabel(agent: string): string {
    return AGENT_LABELS[agent] ?? agent;
  }
}
