<script lang="ts">
	import { page } from '$app/state';
</script>

<div class="flex min-h-screen items-center justify-center bg-white dark:bg-gray-900">
	<div class="text-center">
		<h1 class="text-4xl font-bold text-gray-900 dark:text-gray-100">
			{page.status}
		</h1>
		<p class="mt-2 text-gray-600 dark:text-gray-400">
			{page.error?.message ?? 'Something went wrong'}
		</p>
		<a
			href="/"
			class="mt-4 inline-block rounded-lg bg-blue-500 px-4 py-2 text-white hover:bg-blue-600"
		>
			Back to Home
		</a>
	</div>
</div>
