<script>
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
</script>

<svelte:head>
	<title>{page.status}</title>
</svelte:head>

<div class="hero bg-base-200 min-h-screen">
	<div class="hero-content flex-col lg:flex-row">
		<div class="space-y-4">
			{#if page.status === 404}
				<h1 class="text-5xl font-bold">Not found!</h1>
				<p>The page you are looking for is not found.</p>
				<button class="btn btn-neutral" onclick={() => goto('/')}>Back to Home</button>
			{:else}
				<h1 class="text-5xl font-bold">Something went wrong</h1>
				<p>Something went your during your request.</p>
				<button class="btn btn-neutral" onclick={() => goto('/')}>Back to Home</button>
			{/if}
		</div>
	</div>
</div>
