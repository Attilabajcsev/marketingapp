<script lang="ts">
	import type { UserData } from '$lib/types';
	import { goto } from '$app/navigation';

	let { data }: { data: { user: UserData } } = $props();
	let username: string = $derived(data.user.first_name);

	let loading: boolean = $state(false);
	let errorMessage: string | undefined | null = $state();

	async function getdata() {
		loading = true;
		errorMessage = null;
		try {
			let response = await fetch('api/user/profile/', {
				headers: { Accept: 'application/json' },
				credentials: 'include'
			});

			if (!response.ok) {
				if (response.status === 401) goto('/');
				else errorMessage = response.statusText;
				return;
			}
			const responseJSON = await response.json();

			username = responseJSON.first_name;
			loading = false;
		} catch (err) {
			console.error(err);
		}
	}
</script>

<div
	class="bg-base-neutral relative flex min-h-[90vh] flex-col items-center justify-center gap-8 p-6"
>
	<div class="flex flex-col items-center justify-center">
		{#if username}
			<h1 class="mb-4 p-4 text-4xl font-semibold">Welcome {username}!</h1>
		{:else}
			<h1 class="mb-4 p-4 text-4xl font-semibold">You are now logged in!</h1>
			<p>Try fetching your user data:</p>
		{/if}
	</div>

	{#if errorMessage}
		<div role="alert" class="alert alert-error">
			<button type="button" aria-label="close alert" onclick={() => (errorMessage = null)}>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="h-6 w-6 shrink-0 stroke-current"
					fill="none"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
					/>
				</svg>
			</button>
			<span>{errorMessage}</span>
		</div>
	{/if}

	<div class="flex flex-col items-center justify-center gap-4">
		{#if username}
			<button class="btn btn-neutral min-w-40" onclick={() => (username = '')}>Remove name</button>
		{:else if loading}
			<button class="btn btn-neutral min-w-40" onclick={getdata}>
				<span class="loading loading-spinner loading-sm"></span>
				Getting..</button
			>
		{:else}
			<button class="btn btn-neutral min-w-40" onclick={getdata}>Get name</button>
		{/if}
	</div>
</div>
