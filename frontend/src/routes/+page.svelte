<script lang="ts">
	import { onMount } from 'svelte';
	import { appState } from '$lib/state.svelte';
	import {
		fetchConfig,
		uploadFile,
		startTranscription,
		cancelTranscription,
		pollUntilReady
	} from '$lib/api';
	import FileUpload from '$lib/components/FileUpload.svelte';
	import ModelSelector from '$lib/components/ModelSelector.svelte';
	import LanguageSelector from '$lib/components/LanguageSelector.svelte';
	import ProgressBar from '$lib/components/ProgressBar.svelte';
	import TranscriptionResult from '$lib/components/TranscriptionResult.svelte';
	import ThemeToggle from '$lib/components/ThemeToggle.svelte';

	let ws: WebSocket | null = $state(null);

	const isProcessing = $derived(
		appState.status === 'uploading' || appState.status === 'transcribing'
	);
	const isReady = $derived(appState.startupState === 'ready');
	const canStart = $derived(appState.file !== null && !isProcessing && isReady);

	let stopPolling: (() => void) | null = null;

	onMount(() => {
		stopPolling = pollUntilReady(() => {
			fetchConfig().catch((err) => {
				console.error('Failed to fetch config:', err);
			});
		});

		return () => {
			stopPolling?.();
		};
	});

	async function handleTranscribe() {
		if (!appState.file) return;

		appState.reset();

		try {
			const fileId = await uploadFile(appState.file);
			ws = startTranscription(fileId);
		} catch (err) {
			if (appState.status !== 'error') {
				appState.errorMessage = err instanceof Error ? err.message : 'Unknown error';
				appState.status = 'error';
			}
		}
	}

	function handleCancel() {
		cancelTranscription(ws);
		ws = null;
	}

	function retryStartup() {
		appState.startupState = 'starting';
		appState.startupMessage = 'Reconnecting...';
		appState.startupError = null;
		stopPolling = pollUntilReady(() => {
			fetchConfig().catch((err) => {
				console.error('Failed to fetch config:', err);
			});
		});
	}

	const statusIcon = $derived(
		appState.startupState === 'downloading'
			? '⬇'
			: appState.startupState === 'loading'
				? '⚙'
				: appState.startupState === 'error'
					? '✗'
					: '...'
	);
</script>

<svelte:head>
	<title>Mojiokoshi</title>
</svelte:head>

<div class="mx-auto min-h-screen max-w-4xl px-4 py-8">
	<!-- Header -->
	<header class="mb-8 flex items-center justify-between">
		<div>
			<h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">Mojiokoshi</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				Audio transcription powered by faster-whisper
				{#if appState.config}
					<span
						class="ml-2 rounded-md bg-gray-100 px-2 py-0.5 text-xs dark:bg-gray-800"
					>
						{appState.config.device}
					</span>
				{/if}
			</p>
		</div>
		<ThemeToggle />
	</header>

	{#if !isReady}
		<!-- Startup Status -->
		<div
			class="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-gray-50 p-12 dark:border-gray-700 dark:bg-gray-800/50"
		>
			{#if appState.startupState === 'error'}
				<div class="text-center">
					<div class="mb-3 text-4xl text-red-500">✗</div>
					<p class="mb-2 text-lg font-medium text-red-700 dark:text-red-400">
						{appState.startupMessage}
					</p>
					{#if appState.startupError}
						<p class="mb-4 text-sm text-gray-500 dark:text-gray-400">
							{appState.startupError}
						</p>
					{/if}
					<button
						onclick={retryStartup}
						class="rounded-lg bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600"
					>
						Retry
					</button>
				</div>
			{:else}
				<div class="text-center">
					<div class="mb-4 text-4xl">{statusIcon}</div>
					<p class="mb-2 text-lg font-medium text-gray-900 dark:text-gray-100">
						{appState.startupMessage}
					</p>
					<div class="mx-auto mt-4 h-1.5 w-48 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
						<div class="h-full animate-pulse rounded-full bg-blue-500" style="width: 100%"></div>
					</div>
				</div>
			{/if}
		</div>
	{:else}
		<div class="space-y-6">
			<!-- Upload Section -->
			<FileUpload />

			<!-- Settings -->
			<div class="grid grid-cols-2 gap-4">
				<ModelSelector />
				<LanguageSelector />
			</div>

			<!-- Action Buttons -->
			<div class="flex gap-3">
				{#if isProcessing}
					<button
						onclick={handleCancel}
						class="rounded-lg bg-red-500 px-6 py-2.5 font-medium text-white transition-colors hover:bg-red-600"
					>
						Cancel
					</button>
				{:else}
					<button
						onclick={handleTranscribe}
						disabled={!canStart}
						class="rounded-lg bg-blue-500 px-6 py-2.5 font-medium text-white transition-colors
							hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
					>
						Transcribe
					</button>
				{/if}
			</div>

			<!-- Progress -->
			<ProgressBar />

			<!-- Results -->
			<TranscriptionResult />
		</div>
	{/if}
</div>
