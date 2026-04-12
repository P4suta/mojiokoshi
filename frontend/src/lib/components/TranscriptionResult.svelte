<script lang="ts">
	import { appState } from '$lib/state.svelte';

	let copied = $state(false);

	function formatTime(seconds: number): string {
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		const ms = Math.floor((seconds % 1) * 10);
		return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms}`;
	}

	let copyError = $state('');

	async function copyText() {
		const text = appState.fullText || appState.segments.map((s) => s.text).join('\n');
		try {
			await navigator.clipboard.writeText(text);
			copied = true;
			copyError = '';
			setTimeout(() => (copied = false), 2000);
		} catch {
			copyError = 'Failed to copy. Try selecting and copying manually.';
			setTimeout(() => (copyError = ''), 3000);
		}
	}

	function downloadText() {
		const text = appState.fullText || appState.segments.map((s) => s.text).join('\n');
		const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = 'transcription.txt';
		a.click();
		URL.revokeObjectURL(url);
	}

	const hasContent = $derived(appState.segments.length > 0 || appState.fullText.length > 0);
</script>

{#if hasContent}
	<div class="space-y-3">
		<div class="flex items-center justify-between">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Result</h2>
			<div class="flex gap-2">
				<button
					onclick={copyText}
					class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm transition-colors
						hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700"
				>
					{copied ? 'Copied!' : 'Copy'}
				</button>
				<button
					onclick={downloadText}
					class="rounded-lg border border-gray-300 px-3 py-1.5 text-sm transition-colors
						hover:bg-gray-100 dark:border-gray-600 dark:hover:bg-gray-700"
				>
					Download .txt
				</button>
			</div>
		</div>

		<div
			class="max-h-96 overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-4
				dark:border-gray-700 dark:bg-gray-800/50"
		>
			{#each appState.segments as seg (seg.id)}
				<div class="mb-2 last:mb-0">
					<span class="mr-2 font-mono text-xs text-gray-400 dark:text-gray-500">
						[{formatTime(seg.start)} - {formatTime(seg.end)}]
					</span>
					<span class="text-gray-900 dark:text-gray-100">{seg.text}</span>
				</div>
			{/each}
		</div>
		{#if copyError}
			<p class="text-sm text-amber-600 dark:text-amber-400">{copyError}</p>
		{/if}
	</div>
{/if}

{#if appState.status === 'error'}
	<div class="rounded-lg border border-red-300 bg-red-50 p-4 dark:border-red-700 dark:bg-red-900/20">
		<p class="text-sm text-red-700 dark:text-red-400">{appState.errorMessage}</p>
	</div>
{/if}
