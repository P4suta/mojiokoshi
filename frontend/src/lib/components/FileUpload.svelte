<script lang="ts">
	import { appState } from '$lib/state.svelte';

	let dragOver = $state(false);
	let fileInput: HTMLInputElement;

	const acceptedTypes = '.mp3,.wav,.m4a,.ogg,.flac,.webm,.wma,.aac';

	function handleFile(file: File) {
		appState.file = file;
		appState.reset();
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		const file = e.dataTransfer?.files[0];
		if (file) handleFile(file);
	}

	function onDragOver(e: DragEvent) {
		e.preventDefault();
		dragOver = true;
	}

	function onDragLeave() {
		dragOver = false;
	}

	function onFileSelect(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (file) handleFile(file);
	}

	function formatSize(bytes: number): string {
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}
</script>

<div
	role="button"
	tabindex="0"
	class="cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors
		{dragOver
		? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
		: 'border-gray-300 hover:border-gray-400 dark:border-gray-600 dark:hover:border-gray-500'}"
	ondrop={onDrop}
	ondragover={onDragOver}
	ondragleave={onDragLeave}
	onclick={() => fileInput.click()}
	onkeydown={(e) => e.key === 'Enter' && fileInput.click()}
>
	<input
		bind:this={fileInput}
		type="file"
		accept={acceptedTypes}
		onchange={onFileSelect}
		class="hidden"
	/>

	{#if appState.file}
		<div class="space-y-1">
			<svg class="mx-auto h-8 w-8 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
			</svg>
			<p class="font-medium text-gray-900 dark:text-gray-100">{appState.file.name}</p>
			<p class="text-sm text-gray-500 dark:text-gray-400">{formatSize(appState.file.size)}</p>
			<p class="text-xs text-gray-400 dark:text-gray-500">Click or drop to change file</p>
		</div>
	{:else}
		<div class="space-y-2">
			<svg class="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
			</svg>
			<p class="text-gray-600 dark:text-gray-300">Drop audio file here or click to browse</p>
			<p class="text-sm text-gray-400 dark:text-gray-500">mp3, wav, m4a, ogg, flac, webm</p>
		</div>
	{/if}
</div>
