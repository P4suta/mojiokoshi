<script lang="ts">
	import { appState } from '$lib/state.svelte';

	const languages = $derived(
		appState.config?.languages ?? {
			Japanese: 'ja',
			English: 'en',
			Chinese: 'zh',
			Korean: 'ko',
			'Auto-detect': 'auto'
		}
	);
</script>

<div class="space-y-1">
	<label for="language-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
		Language
	</label>
	<select
		id="language-select"
		bind:value={appState.language}
		disabled={appState.status === 'transcribing'}
		class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm
			focus:border-blue-500 focus:ring-1 focus:ring-blue-500
			disabled:opacity-50
			dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
	>
		{#each Object.entries(languages) as [name, code]}
			<option value={code}>{name}</option>
		{/each}
	</select>
</div>
