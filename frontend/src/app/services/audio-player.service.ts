import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class AudioPlayerService {
  private currentAudio: HTMLAudioElement | null = null;

  playBase64(base64Mp3: string): void {
    this.stop();
    const audio = new Audio(`data:audio/mpeg;base64,${base64Mp3}`);
    this.currentAudio = audio;
    audio.play().catch((e) => console.warn('Audio play blocked:', e));
  }

  stop(): void {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }
  }
}
