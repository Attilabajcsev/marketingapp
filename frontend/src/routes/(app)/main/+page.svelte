<script lang="ts">
	import type { UserData } from '$lib/types';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';

	let { data }: { data: { user: UserData } } = $props();
	let username: string = $derived(data.user.first_name);

	let loading: boolean = $state(false);
	let errorMessage: string | undefined | null = $state();

	// Campaign types and state
	type Campaign = {
		id: number;
		title: string;
		content: string;
		guideline_type?: string;
		uploaded_at: string;
	};

	let campaigns: Campaign[] = $state([]);
	let campaignsLoading: boolean = $state(true);
	let createLoading: boolean = $state(false);
	let newTitle: string = $state('');
	let newContent: string = $state('');
	let newType: string = $state('tone');

	// Simple prompt placeholder
	let userPrompt: string = $state('');

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

	async function loadCampaigns() {
		campaignsLoading = true;
		errorMessage = null;
		try {
			const response = await fetch('api/brand-guidelines/', {
				headers: { Accept: 'application/json' },
				credentials: 'include'
			});
			if (!response.ok) {
				if (response.status === 401) return goto('/login');
				errorMessage = response.statusText;
				campaignsLoading = false;
				return;
			}
			const data: Campaign[] = await response.json();
			campaigns = data ?? [];
			campaignsLoading = false;
		} catch (err) {
			console.error(err);
			errorMessage = 'Failed to load campaigns';
			campaignsLoading = false;
		}
	}

	async function createCampaign() {
		if (!newTitle.trim() || !newContent.trim()) return;
		createLoading = true;
		errorMessage = null;
		try {
			const response = await fetch('api/brand-guidelines/create/', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ title: newTitle.trim(), content: newContent.trim(), guideline_type: newType })
			});
			if (!response.ok) {
				if (response.status === 401) return goto('/login');
				errorMessage = response.statusText;
				createLoading = false;
				return;
			}
			await loadCampaigns();
			newTitle = '';
			newContent = '';
			newType = 'tone';
			createLoading = false;
		} catch (err) {
			console.error(err);
			errorMessage = 'Failed to create campaign';
			createLoading = false;
		}
	}

	function submitPrompt() {
		if (!userPrompt.trim()) return;
		// Placeholder action
		console.log('User prompt submitted:', userPrompt);
	}

	onMount(loadCampaigns);
</script>

<div class="bg-base-neutral relative min-h-[90vh] p-6">
	<div class="mb-6 flex flex-col items-center justify-center">
		{#if username}
			<h1 class="mb-2 p-2 text-3xl font-semibold">Welcome {username}!</h1>
		{:else}
			<h1 class="mb-2 p-2 text-3xl font-semibold">You are now logged in!</h1>
			<p>Try fetching your user data:</p>
		{/if}
		<div class="mt-2">
			{#if username}
				<button class="btn btn-neutral min-w-40" onclick={() => (username = '')}>Remove name</button>
			{:else if loading}
				<button class="btn btn-neutral min-w-40" onclick={getdata}>
					<span class="loading loading-spinner loading-sm"></span>
					Getting..
				</button>
			{:else}
				<button class="btn btn-neutral min-w-40" onclick={getdata}>Get name</button>
			{/if}
		</div>
	</div>

	{#if errorMessage}
		<div role="alert" class="alert alert-error mb-4">
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

	<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
		<!-- Campaigns list -->
		<div class="card bg-base-200">
			<div class="card-body">
				<div class="mb-2 flex items-center justify-between">
					<h2 class="card-title">Your Brand Guidelines</h2>
					<button class="btn btn-sm" onclick={loadCampaigns} disabled={campaignsLoading}>
						{#if campaignsLoading}
							<span class="loading loading-spinner loading-xs"></span>
							Refreshing
						{:else}
							Refresh
						{/if}
					</button>
				</div>

				{#if campaignsLoading}
					<div class="flex items-center justify-center p-6">
						<span class="loading loading-spinner loading-lg"></span>
					</div>
				{:else if campaigns.length === 0}
					<p class="opacity-70">No guidelines yet. Create one on the right.</p>
				{:else}
					<div class="overflow-x-auto">
						<table class="table table-zebra w-full">
							<thead>
								<tr>
									<th>Title</th>
									<th>Type</th>
									<th>Created</th>
								</tr>
							</thead>
							<tbody>
								{#each campaigns as c}
									<tr>
										<td class="font-medium">{c.title}</td>
										<td class="uppercase text-xs opacity-70">{c.guideline_type}</td>
										<td>{new Date(c.uploaded_at).toLocaleString()}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		</div>

		<!-- Create campaign + Prompt -->
		<div class="flex flex-col gap-6">
			<div class="card bg-base-200">
				<div class="card-body gap-3">
					<h2 class="card-title">Create Guideline</h2>
					<input
						class="input input-bordered"
						type="text"
						placeholder="Guideline title"
						bind:value={newTitle}
					/>
					<select class="select select-bordered" bind:value={newType}>
						<option value="tone">Tone of Voice</option>
						<option value="terminology">Company Terminology</option>
						<option value="style">Writing Style</option>
						<option value="rules">Content Rules</option>
					</select>
					<textarea
						class="textarea textarea-bordered min-h-28"
						placeholder="Guideline content (tone, rules, etc.)"
						bind:value={newContent}
					/>
					<button class="btn btn-neutral" onclick={createCampaign} disabled={createLoading}>
						{#if createLoading}
							<span class="loading loading-spinner loading-sm"></span>
							Creating
						{:else}
							Create
						{/if}
					</button>
				</div>
			</div>

			<div class="card bg-base-200">
				<div class="card-body gap-3">
					<h2 class="card-title">Prompt</h2>
					<textarea
						class="textarea textarea-bordered min-h-28"
						placeholder="Describe what you want to generate..."
						bind:value={userPrompt}
					/>
					<button class="btn" onclick={submitPrompt}>Submit</button>
				</div>
			</div>
		</div>
	</div>
</div>
