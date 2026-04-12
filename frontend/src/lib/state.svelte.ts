export interface Segment {
	id: number;
	start: number;
	end: number;
	text: string;
}

export interface AppConfig {
	models: string[];
	languages: Record<string, string>;
	default_model: string;
	default_language: string;
	device: string;
}

export type TranscriptionStatus = 'idle' | 'uploading' | 'transcribing' | 'done' | 'error';

export type StartupState = 'starting' | 'downloading' | 'loading' | 'ready' | 'error';

class AppState {
	file = $state<File | null>(null);
	modelSize = $state('large-v3');
	language = $state('ja');
	segments = $state<Segment[]>([]);
	fullText = $state('');
	status = $state<TranscriptionStatus>('idle');
	progress = $state(0);
	elapsedSeconds = $state(0);
	lastSegmentTime = $state(0);
	totalElapsedSeconds = $state<number | null>(null);
	errorMessage = $state('');
	config = $state<AppConfig | null>(null);

	startupState = $state<StartupState>('starting');
	startupMessage = $state('Connecting to server...');
	startupError = $state<string | null>(null);

	reset() {
		this.segments = [];
		this.fullText = '';
		this.status = 'idle';
		this.progress = 0;
		this.elapsedSeconds = 0;
		this.lastSegmentTime = 0;
		this.totalElapsedSeconds = null;
		this.errorMessage = '';
	}
}

export const appState = new AppState();
