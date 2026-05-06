import { Injectable, OnDestroy } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { environment } from '../../environments/environment';
import { WsMessage, WsResult } from '../models/notebook.models';

@Injectable({ providedIn: 'root' })
export class WebSocketService implements OnDestroy {
  private socket: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  private connected$ = new BehaviorSubject<boolean>(false);
  private messages$ = new Subject<WsResult>();

  readonly isConnected$ = this.connected$.asObservable();
  readonly messages: Observable<WsResult> = this.messages$.asObservable();

  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) return;

    const wsUrl = environment.wsUrl ||
      `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;
    this.socket = new WebSocket(wsUrl);

    this.socket.onopen = () => {
      this.connected$.next(true);
    };

    this.socket.onmessage = (event) => {
      try {
        const data: WsResult = JSON.parse(event.data);
        this.messages$.next(data);
      } catch {
        console.error('WS parse error', event.data);
      }
    };

    this.socket.onclose = () => {
      this.connected$.next(false);
      this.scheduleReconnect();
    };

    this.socket.onerror = () => {
      this.socket?.close();
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.socket?.close();
    this.socket = null;
  }

  send(message: WsMessage): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    }
  }

  sendAudio(audioBlob: Blob, wakeWord: 'save' | 'respond'): Promise<void> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(',')[1];
        this.send({ type: 'audio', wake_word: wakeWord, data: base64 });
        resolve();
      };
      reader.onerror = reject;
      reader.readAsDataURL(audioBlob);
    });
  }

  resetConversation(): void {
    this.send({ type: 'reset' });
  }

  private scheduleReconnect(): void {
    this.reconnectTimer = setTimeout(() => this.connect(), 3000);
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}
