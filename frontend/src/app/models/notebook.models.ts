export type WakeWordType = 'save' | 'respond';
export type Intent = 'save_note' | 'add_calendar' | 'respond' | 'unknown';
export type NoteCategory = 'address' | 'thought' | 'task' | 'event' | 'general';
export type AppStatus =
  | 'idle'
  | 'listening'
  | 'recording'
  | 'processing'
  | 'responding';

export interface WsMessage {
  type: 'audio' | 'reset';
  wake_word?: WakeWordType;
  data?: string; // base64 audio
}

export interface WsResult {
  type: 'result' | 'status' | 'error';
  // result
  transcription?: string;
  intent?: Intent;
  category?: NoteCategory;
  response_text?: string;
  saved_id?: string;
  enrichment?: string;
  audio?: string; // base64 MP3
  error?: string;
  // status
  message?: string;
}

export interface Note {
  id: string;
  created_at: string;
  category: NoteCategory;
  content: string;
  raw_transcription: string;
  enrichment?: string;
}

export interface NotesResponse {
  address: Note[];
  thought: Note[];
  task: Note[];
  event: Note[];
  general: Note[];
}

export interface CalendarEvent {
  id: string;
  created_at: string;
  title: string;
  date: string;
  time?: string;
  description?: string;
  location?: string;
}

export const CATEGORY_CONFIG: Record<
  NoteCategory,
  { label: string; icon: string; color: string }
> = {
  address: { label: 'Adresy', icon: 'place', color: '#4fc3f7' },
  thought: { label: 'Myśli', icon: 'lightbulb', color: '#fff176' },
  task: { label: 'Zadania', icon: 'task_alt', color: '#a5d6a7' },
  event: { label: 'Wydarzenia', icon: 'event', color: '#ce93d8' },
  general: { label: 'Ogólne', icon: 'notes', color: '#ffcc80' },
};
