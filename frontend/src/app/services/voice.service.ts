import { Injectable, NgZone, OnDestroy } from '@angular/core';
import { BehaviorSubject, Subject } from 'rxjs';
import { WakeWordType } from '../models/notebook.models';
import type {
  SpeechRecognition,
  SpeechRecognitionConstructor,
  SpeechRecognitionErrorEvent,
  SpeechRecognitionEvent,
} from './speech-recognition.types';

export interface VoiceEvent {
  wakeWord: WakeWordType;
  audioBlob: Blob;
}

// Rozszerzenie Window o Web Speech API (prefixowane i standardowe)
interface SpeechWindow {
  SpeechRecognition?: SpeechRecognitionConstructor;
  webkitSpeechRecognition?: SpeechRecognitionConstructor;
}

// Parametry VAD (Voice Activity Detection)
const VAD_SILENCE_THRESHOLD = 0.01;   // próg głośności poniżej którego = cisza
const VAD_SILENCE_DURATION_MS = 2000; // 2s ciszy → zatrzymaj nagranie
const VAD_MAX_DURATION_MS = 30_000;   // max 30s nagrania

@Injectable({ providedIn: 'root' })
export class VoiceService implements OnDestroy {
  private recognition: SpeechRecognition | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private activeWakeWord: WakeWordType | null = null;

  // VAD – detekcja ciszy przez Web Audio API
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private vadTimer: ReturnType<typeof setTimeout> | null = null;
  private maxTimer: ReturnType<typeof setTimeout> | null = null;
  private vadInterval: ReturnType<typeof setInterval> | null = null;

  private isListening$ = new BehaviorSubject<boolean>(false);
  private isRecording$ = new BehaviorSubject<boolean>(false);
  private voiceEvent$ = new Subject<VoiceEvent>();
  private statusMsg$ = new BehaviorSubject<string>('Naciśnij mikrofon, aby aktywować');

  readonly isListening = this.isListening$.asObservable();
  readonly isRecording = this.isRecording$.asObservable();
  readonly voiceEvent = this.voiceEvent$.asObservable();
  readonly statusMessage = this.statusMsg$.asObservable();

  // Hasła aktywujące – wiele wariantów (Web Speech API nie zawsze wstawia przecinek)
  private readonly WAKE_WORDS_SAVE = [
    'notatnik zapisz', 'notatnik, zapisz',
    'notatniku zapisz', 'notatniku, zapisz',
  ];
  private readonly WAKE_WORDS_RESPOND = [
    'notatnik powiedz', 'notatnik, powiedz',
    'notatniku powiedz', 'notatniku, powiedz',
  ];
  // Wzorzec do wycinania hasła z transkrypcji Whisper (fix #1)
  private readonly STRIP_WAKE_REGEX =
    /^(notatniku?,\s*)?(zapisz|powiedz)[,:]?\s*/i;

  constructor(private zone: NgZone) {}

  get supported(): boolean {
    return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
  }

  // ── Nasłuchiwanie na hasło ──────────────────────────────────────────────

  startListening(): void {
    if (!this.supported) {
      this.statusMsg$.next('Przeglądarka nie obsługuje rozpoznawania mowy. Użyj Chrome.');
      return;
    }
    if (this.isListening$.value) return;

    this._startRecognition();
    this.isListening$.next(true);
    this.statusMsg$.next('Nasłuchuję... Powiedz „Notatnik, zapisz" lub „Notatnik, powiedz"');
  }

  stopListening(): void {
    this.recognition?.abort();
    this.recognition = null;
    this.isListening$.next(false);
    this._stopRecording(false);
    this.statusMsg$.next('Naciśnij mikrofon, aby aktywować');
  }

  private _startRecognition(): void {
    const win = window as unknown as SpeechWindow;
    const SpeechRecognitionClass = win.SpeechRecognition ?? win.webkitSpeechRecognition;

    if (!SpeechRecognitionClass) return;

    const rec: SpeechRecognition = new SpeechRecognitionClass();
    rec.lang = 'pl-PL';
    rec.continuous = true;
    rec.interimResults = true;
    this.recognition = rec;

    rec.onresult = (event: SpeechRecognitionEvent) => {
      this.zone.run(() => {
        const results = Array.from({ length: event.results.length }, (_, i) => event.results[i]);
        const transcript = results
          .map((r) => r[0].transcript)
          .join(' ')
          .toLowerCase()
          .trim();
        this._checkForWakeWord(transcript);
      });
    };

    rec.onerror = (e: SpeechRecognitionErrorEvent) => {
      // 'aborted' = celowe przerwanie (nagrywanie), ignoruj
      if (e.error === 'aborted') return;
      this.zone.run(() => {
        if (this.isListening$.value && !this.isRecording$.value) {
          setTimeout(() => this._startRecognition(), 1000);
        }
      });
    };

    rec.onend = () => {
      this.zone.run(() => {
        // Restart nasłuchiwania po zakończeniu nagrania (fix #3 – brak konfliktu)
        if (this.isListening$.value && !this.isRecording$.value) {
          setTimeout(() => this._startRecognition(), 300);
        }
      });
    };

    rec.start();
  }

  // ── Detekcja hasła ──────────────────────────────────────────────────────

  private _checkForWakeWord(transcript: string): void {
    if (this.isRecording$.value) return;

    const isSave = this.WAKE_WORDS_SAVE.some((w) => transcript.includes(w));
    const isRespond = this.WAKE_WORDS_RESPOND.some((w) => transcript.includes(w));

    if (isSave || isRespond) {
      const type: WakeWordType = isSave ? 'save' : 'respond';
      this.activeWakeWord = type;

      // WAŻNE: zatrzymaj Speech Recognition przed startem MediaRecorder (fix #3)
      this.recognition?.abort();
      this.recognition = null;

      this.statusMsg$.next(isSave ? 'Słucham... Powiedz notatkę' : 'Słucham... Zadaj pytanie');
      this._startRecording(type);
    }
  }

  // ── Nagrywanie z VAD ────────────────────────────────────────────────────

  private async _startRecording(wakeWord: WakeWordType): Promise<void> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioChunks = [];

      // Web Audio API do detekcji ciszy (VAD) (fix #2)
      this.audioContext = new AudioContext();
      const source = this.audioContext.createMediaStreamSource(stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 512;
      source.connect(this.analyser);

      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      });

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.audioChunks.push(e.data);
      };

      this.mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        this._cleanupVad();

        const blob = new Blob(this.audioChunks, { type: 'audio/webm' });

        this.zone.run(() => {
          this.isRecording$.next(false);
          if (this.activeWakeWord && blob.size > 1000) {
            this.voiceEvent$.next({ wakeWord: this.activeWakeWord, audioBlob: blob });
          }
          this.activeWakeWord = null;
          this.statusMsg$.next('Przetwarzam...');

          // Wznów nasłuchiwanie po zakończeniu nagrania
          if (this.isListening$.value) {
            setTimeout(() => this._startRecognition(), 500);
          }
        });
      };

      this.mediaRecorder.start(100);
      this.isRecording$.next(true);
      this._startVad();

    } catch {
      this.statusMsg$.next('Brak dostępu do mikrofonu.');
      this.activeWakeWord = null;
      if (this.isListening$.value) {
        setTimeout(() => this._startRecognition(), 500);
      }
    }
  }

  stopRecording(): void {
    this._stopRecording(true);
  }

  private _stopRecording(emitEvent: boolean): void {
    if (!emitEvent) this.activeWakeWord = null;
    this._cleanupVad();
    if (this.mediaRecorder?.state === 'recording') {
      this.mediaRecorder.stop();
    }
  }

  // ── VAD – detekcja ciszy przez AudioContext ─────────────────────────────

  private _startVad(): void {
    const dataArray = new Float32Array(this.analyser!.fftSize);
    let silenceStart: number | null = null;

    this.vadInterval = setInterval(() => {
      this.analyser!.getFloatTimeDomainData(dataArray);
      const rms = Math.sqrt(dataArray.reduce((s, v) => s + v * v, 0) / dataArray.length);

      if (rms < VAD_SILENCE_THRESHOLD) {
        if (silenceStart === null) silenceStart = Date.now();
        else if (Date.now() - silenceStart > VAD_SILENCE_DURATION_MS) {
          // 2 sekundy ciszy → zatrzymaj nagranie
          this._stopRecording(true);
        }
      } else {
        silenceStart = null; // mowa wykryta → resetuj licznik ciszy
      }
    }, 100);

    // Bezpieczny limit maksymalny
    this.maxTimer = setTimeout(() => this._stopRecording(true), VAD_MAX_DURATION_MS);
  }

  private _cleanupVad(): void {
    if (this.vadInterval) { clearInterval(this.vadInterval); this.vadInterval = null; }
    if (this.vadTimer) { clearTimeout(this.vadTimer); this.vadTimer = null; }
    if (this.maxTimer) { clearTimeout(this.maxTimer); this.maxTimer = null; }
    this.audioContext?.close();
    this.audioContext = null;
    this.analyser = null;
  }

  // Getter używany przez AppComponent do sprawdzenia stanu
  get isCurrentlyListening(): boolean {
    return this.isListening$.value;
  }

  // Wzorzec do wycinania hasła – eksportowany dla backendu (info dla serwera)
  get stripWakeRegex(): RegExp {
    return this.STRIP_WAKE_REGEX;
  }

  ngOnDestroy(): void {
    this.stopListening();
  }
}
