<script lang="ts">
	import { appState } from '$lib/state.svelte';

	const HANG_THRESHOLD_MS = 30_000;

	function formatTime(seconds: number): string {
		const m = Math.floor(seconds / 60);
		const s = seconds % 60;
		return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
	}

	const isActive = $derived(
		appState.status === 'uploading' || appState.status === 'transcribing'
	);

	const statusText = $derived(
		appState.status === 'uploading' ? 'Uploading...' : 'Transcribing...'
	);

	const eta = $derived.by(() => {
		if (appState.progress >= 5 && appState.elapsedSeconds > 0) {
			const remaining = ((100 - appState.progress) * appState.elapsedSeconds) / appState.progress;
			return Math.ceil(remaining);
		}
		return null;
	});

	const isHanging = $derived(
		appState.status === 'transcribing' &&
			appState.lastSegmentTime > 0 &&
			Date.now() - appState.lastSegmentTime > HANG_THRESHOLD_MS
	);

	const doneText = $derived.by(() => {
		if (appState.status !== 'done') return '';
		const total = appState.totalElapsedSeconds;
		if (total !== null) {
			return `Completed in ${total.toFixed(1)}s (${appState.segments.length} segments)`;
		}
		return `Completed (${appState.segments.length} segments)`;
	});
</script>

{#if isActive}
	<div class="space-y-2">
		<div class="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
			<span>{statusText} {appState.segments.length} segments</span>
			<div class="flex gap-3">
				<span>{formatTime(appState.elapsedSeconds)} elapsed</span>
				{#if appState.progress > 0}
					<span>{appState.progress}%</span>
				{/if}
				{#if eta !== null}
					<span class="text-blue-500">ETA ~{formatTime(eta)}</span>
				{/if}
			</div>
		</div>
		<div class="h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
			{#if appState.progress > 0}
				<div
					class="h-full rounded-full bg-blue-500 transition-all duration-500"
					style="width: {appState.progress}%"
				></div>
			{:else}
				<div class="h-full animate-pulse rounded-full bg-blue-400" style="width: 100%"></div>
			{/if}
		</div>
		{#if isHanging}
			<p class="text-sm text-amber-600 dark:text-amber-400">
				Processing is taking longer than expected. The model may be working on a difficult section...
			</p>
		{/if}
	</div>
{/if}

{#if appState.status === 'done' && doneText}
	<p class="text-sm text-green-600 dark:text-green-400">{doneText}</p>
{/if}
