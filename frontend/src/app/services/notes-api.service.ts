import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { CalendarEvent, NotesResponse } from '../models/notebook.models';

@Injectable({ providedIn: 'root' })
export class NotesApiService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getNotes(category = '', limit = 50): Observable<NotesResponse> {
    let params = new HttpParams().set('limit', limit);
    if (category) params = params.set('category', category);
    return this.http.get<NotesResponse>(`${this.base}/api/notes`, { params });
  }

  searchNotes(
    query: string,
    category = '',
    limit = 5
  ): Observable<{ query: string; results: string }> {
    let params = new HttpParams().set('q', query).set('limit', limit);
    if (category) params = params.set('category', category);
    return this.http.get<{ query: string; results: string }>(
      `${this.base}/api/notes/search`,
      { params }
    );
  }

  getCalendar(dateFrom = '', dateTo = ''): Observable<CalendarEvent[]> {
    let params = new HttpParams();
    if (dateFrom) params = params.set('date_from', dateFrom);
    if (dateTo) params = params.set('date_to', dateTo);
    return this.http.get<CalendarEvent[]>(`${this.base}/api/calendar`, { params });
  }

  getCategories(): Observable<Record<string, number>> {
    return this.http.get<Record<string, number>>(`${this.base}/api/categories`);
  }
}
