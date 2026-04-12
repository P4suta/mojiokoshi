<script lang="ts">
	import { appState } from '$lib/state.svelte';

	const currentModel = $derived(appState.config?.default_model ?? appState.modelSize);
</script>

<div class="space-y-1">
	<label for="model-display" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
		Model
	</label>
	<div
		id="model-display"
		class="w-full rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 text-sm
			dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100"
	>
		{currentModel}
	</div>
	<p class="text-xs text-gray-400 dark:text-gray-500">Set at server startup</p>
</div>
