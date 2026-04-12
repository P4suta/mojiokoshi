import { appState, type Segment, type StartupState } from './state.svelte';

const FETCH_TIMEOUT_MS = 30_000;
const WS_RECONNECT_DELAY_MS = 1_000;

class ApiError extends Error {
	constructor(
		message: string,
		public readonly statusCode?: number
	) {
		super(message);
		this.name = 'ApiError';
	}
}

async function fetchWithTimeout(
	input: RequestInfo | URL,
	init?: RequestInit,
	timeoutMs: number = FETCH_TIMEOUT_MS
): Promise<Response> {
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

	try {
		const response = await fetch(input, {
			...init,
			signal: controller.signal
		});
		return response;
	} catch (error) {
		if (error instanceof DOMException && error.name === 'AbortError') {
			throw new ApiError(`Request timed out after ${timeoutMs}ms`);
		}
		if (error instanceof TypeError) {
			throw new ApiError('Network error: unable to connect to the server');
		}
		throw error;
	} finally {
		clearTimeout(timeoutId);
	}
}

async function parseErrorResponse(resp: Response): Promise<string> {
	try {
		const data = await resp.json();
		return data.detail || data.message || `HTTP ${resp.status}`;
	} catch {
		return `HTTP ${resp.status}: ${resp.statusText}`;
	}
}

export interface StatusResponse {
	state: StartupState;
	message: string;
	ready: boolean;
	error: string | null;
}

export async function fetchStatus(): Promise<StatusResponse> {
	const resp = await fetchWithTimeout('/api/status', undefined, 5000);
	if (!resp.ok) {
		throw new ApiError('Failed to fetch status', resp.status);
	}
	return resp.json();
}

export function pollUntilReady(onReady: () => void): () => void {
	let stopped = false;

	async function poll() {
		while (!stopped) {
			try {
				const status = await fetchStatus();
				appState.startupState = status.state;
				appState.startupMessage = status.message;
				appState.startupError = status.error;

				if (status.ready) {
					onReady();
					return;
				}
				if (status.state === 'error') {
					return;
				}
			} catch {
				appState.startupMessage = 'Connecting to server...';
			}

			await new Promise((r) => setTimeout(r, 1500));
		}
	}

	poll();
	return () => {
		stopped = true;
	};
}

export async function fetchConfig(): Promise<void> {
	try {
		const resp = await fetchWithTimeout('/api/config');
		if (!resp.ok) {
			const message = await parseErrorResponse(resp);
			throw new ApiError(message, resp.status);
		}
		appState.config = await resp.json();
		appState.modelSize = appState.config!.default_model;
		appState.language = appState.config!.default_language;
	} catch (error) {
		if (error instanceof ApiError) {
			appState.errorMessage = `Failed to load config: ${error.message}`;
		} else {
			appState.errorMessage = 'Failed to connect to server';
		}
		appState.status = 'error';
		throw error;
	}
}

export async function uploadFile(file: File): Promise<string> {
	const formData = new FormData();
	formData.append('file', file);

	appState.status = 'uploading';

	const resp = await fetchWithTimeout('/api/upload', {
		method: 'POST',
		body: formData
	});

	if (!resp.ok) {
		const message = await parseErrorResponse(resp);
		appState.status = 'error';
		appState.errorMessage = message;
		throw new ApiError(message, resp.status);
	}

	const data = await resp.json();
	return data.file_id;
}

let elapsedTimer: ReturnType<typeof setInterval> | null = null;

function startElapsedTimer() {
	const startTime = Date.now();
	appState.elapsedSeconds = 0;
	appState.lastSegmentTime = Date.now();
	elapsedTimer = setInterval(() => {
		appState.elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
	}, 1000);
}

function stopElapsedTimer() {
	if (elapsedTimer !== null) {
		clearInterval(elapsedTimer);
		elapsedTimer = null;
	}
}

export function startTranscription(fileId: string): WebSocket {
	const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
	const ws = new WebSocket(`${protocol}//${window.location.host}/api/ws/transcribe`);

	appState.status = 'transcribing';
	appState.segments = [];
	appState.fullText = '';
	appState.progress = 0;
	appState.totalElapsedSeconds = null;

	ws.onopen = () => {
		startElapsedTimer();
		ws.send(
			JSON.stringify({
				type: 'start',
				file_id: fileId,
				model_size: appState.modelSize,
				language: appState.language
			})
		);
	};

	ws.onmessage = (event) => {
		let msg: Record<string, unknown>;
		try {
			msg = JSON.parse(event.data);
		} catch {
			appState.errorMessage = 'Received invalid data from server';
			appState.status = 'error';
			stopElapsedTimer();
			return;
		}

		switch (msg.type) {
			case 'segment': {
				const seg = msg.segment as Segment;
				if (seg && typeof seg.id === 'number' && typeof seg.text === 'string') {
					appState.segments = [...appState.segments, seg];
					appState.lastSegmentTime = Date.now();
				}
				break;
			}
			case 'progress':
				if (typeof msg.percent === 'number') {
					appState.progress = msg.percent;
				}
				break;
			case 'done':
				stopElapsedTimer();
				appState.fullText = (msg.full_text as string) ?? '';
				appState.totalElapsedSeconds =
					typeof msg.elapsed_seconds === 'number' ? msg.elapsed_seconds : null;
				appState.progress = 100;
				appState.status = 'done';
				break;
			case 'error':
				stopElapsedTimer();
				appState.errorMessage = (msg.message as string) ?? 'Unknown server error';
				appState.status = 'error';
				break;
		}
	};

	ws.onerror = () => {
		stopElapsedTimer();
		appState.errorMessage = 'WebSocket connection error. Is the server running?';
		appState.status = 'error';
	};

	ws.onclose = (event) => {
		if (appState.status === 'transcribing') {
			stopElapsedTimer();
			if (event.code === 1000) {
				return;
			}
			appState.status = 'error';
			appState.errorMessage = `Connection closed unexpectedly (code: ${event.code})`;
		}
	};

	return ws;
}

export function cancelTranscription(ws: WebSocket | null): void {
	stopElapsedTimer();
	if (ws && ws.readyState === WebSocket.OPEN) {
		try {
			ws.send(JSON.stringify({ type: 'cancel' }));
		} catch {
			// Connection may already be closing
		}
		ws.close();
	}
	appState.reset();
}
