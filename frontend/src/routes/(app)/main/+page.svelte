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

	// Edit guideline state
	let editingId: number | null = $state(null);
	let editTitle: string = $state('');
	let editType: string = $state('tone');
	let editContent: string = $state('');

	function startEdit(c: Campaign) {
		editingId = c.id;
		editTitle = c.title;
		editType = c.guideline_type || 'tone';
		editContent = c.content;
	}

	async function saveEdit() {
		if (editingId == null) return;
		const res = await fetch(`api/brand-guidelines/${editingId}/`, {
			method: 'PUT',
			credentials: 'include',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ title: editTitle, content: editContent, guideline_type: editType })
		});
		if (res.ok) {
			await loadCampaigns();
			editingId = null;
		}
	}

	async function deleteGuideline(id: number) {
		if (!confirm('Delete this guideline?')) return;
		const res = await fetch(`api/brand-guidelines/${id}/`, { method: 'DELETE', credentials: 'include' });
		if (res.ok) await loadCampaigns();
	}

	let campaigns: Campaign[] = $state([]);
	let campaignsLoading: boolean = $state(true);
	let createLoading: boolean = $state(false);
	let newTitle: string = $state('');
	let newContent: string = $state('');
	let newType: string = $state('tone');

	// Simple prompt placeholder
	let userPrompt: string = $state('');

	// Uploads state
	type UploadItem = {
		id: number;
		filename: string;
		file_type: string;
		upload_date: string;
		campaign_count: number;
	};
	let uploads: UploadItem[] = $state([]);
	let uploadsLoading: boolean = $state(false);
	let uploadBusy: boolean = $state(false);
	let fileToUpload: File | null = $state(null);
	let showUploadModal: boolean = $state(false);
	let selectedUpload: (UploadItem & { parsed_campaigns?: { title: string; content: string; meta?: Record<string, unknown> }[] }) | null = $state(null);

	async function openUploadDetail(id: number) {
		try {
			const res = await fetch(`api/uploaded-campaigns/${id}/`, { credentials: 'include' });
			if (!res.ok) return;
			selectedUpload = await res.json();
			showUploadModal = true;
		} catch (e) {
			console.error(e);
		}
	}

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

	async function loadUploads() {
		uploadsLoading = true;
		try {
			const res = await fetch('api/uploaded-campaigns/', { credentials: 'include' });
			if (res.ok) uploads = await res.json();
		} catch (e) {
			console.error(e);
		} finally {
			uploadsLoading = false;
		}
	}

	async function uploadFile() {
		if (!fileToUpload) return;
		uploadBusy = true;
		try {
			const form = new FormData();
			form.append('file', fileToUpload);
			const res = await fetch('api/uploaded-campaigns/upload/', {
				method: 'POST',
				credentials: 'include',
				body: form
			});
			if (!res.ok) {
				console.error('Upload failed');
				return;
			}
			await loadUploads();
			fileToUpload = null;
		} catch (e) {
			console.error(e);
		} finally {
			uploadBusy = false;
		}
	}

	async function deleteUpload(id: number) {
		if (!confirm('Delete this upload?')) return;
		const res = await fetch(`api/uploaded-campaigns/${id}/`, { method: 'DELETE', credentials: 'include' });
		if (res.ok) await loadUploads();
	}

	onMount(loadCampaigns);
	onMount(loadUploads);
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
										<td class="font-medium">
											{#if editingId === c.id}
												<input class="input input-sm input-bordered w-full" bind:value={editTitle} />
											{:else}
												{c.title}
											{/if}
										</td>
										<td class="uppercase text-xs opacity-70">
											{#if editingId === c.id}
												<select class="select select-bordered select-sm" bind:value={editType}>
													<option value="tone">tone</option>
													<option value="terminology">terminology</option>
													<option value="style">style</option>
													<option value="rules">rules</option>
												</select>
											{:else}
												{c.guideline_type}
											{/if}
										</td>
										<td>
											{#if editingId === c.id}
												<textarea class="textarea textarea-bordered textarea-sm w-full" bind:value={editContent} />
											{:else}
												{new Date(c.uploaded_at).toLocaleString()}
											{/if}
										</td>
										<td class="w-44 text-right">
											{#if editingId === c.id}
												<button class="btn btn-xs btn-neutral mr-2" onclick={saveEdit}>Save</button>
												<button class="btn btn-xs" onclick={() => (editingId = null)}>Cancel</button>
											{:else}
												<button class="btn btn-xs mr-2" onclick={() => startEdit(c)}>Edit</button>
												<button class="btn btn-xs btn-error" onclick={() => deleteGuideline(c.id)}>Delete</button>
											{/if}
										</td>
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
			<!-- Uploads -->
			<div class="card bg-base-200">
				<div class="card-body gap-3">
					<div class="flex items-center justify-between">
						<h2 class="card-title">Upload Past Campaigns</h2>
						<button class="btn btn-sm" onclick={loadUploads} disabled={uploadsLoading}>
							{#if uploadsLoading}
								<span class="loading loading-spinner loading-xs"></span>
								Refreshing
							{:else}
								Refresh
							{/if}
						</button>
					</div>
					<input class="file-input file-input-bordered w-full" type="file" accept=".csv,.txt,.json" onchange={(e: Event) => { const t = e.target as HTMLInputElement; fileToUpload = (t.files && t.files[0]) || null; }} />
					<button class="btn btn-neutral" onclick={uploadFile} disabled={uploadBusy || !fileToUpload}>
						{#if uploadBusy}
							<span class="loading loading-spinner loading-sm"></span>
							Uploading
						{:else}
							Upload
						{/if}
					</button>

					{#if uploads.length > 0}
						<div class="overflow-x-auto">
							<table class="table w-full">
								<thead>
									<tr>
										<th>Filename</th>
										<th>Type</th>
										<th>Uploaded</th>
										<th># Campaigns</th>
									</tr>
								</thead>
								<tbody>
									{#each uploads as u}
										<tr>
											<td><a class="link link-primary" href="#" onclick={() => openUploadDetail(u.id)}>{u.filename}</a></td>
											<td class="uppercase text-xs opacity-70">{u.file_type}</td>
											<td>{new Date(u.upload_date).toLocaleString()}</td>
											<td class="flex items-center gap-2">
												<span>{u.campaign_count}</span>
												<button class="btn btn-xs btn-error ml-auto" onclick={() => deleteUpload(u.id)}>Delete</button>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{:else}
						<p class="opacity-70">No uploads yet. Upload a CSV/TXT/JSON file.</p>
					{/if}
				</div>
			</div>

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

{#if showUploadModal && selectedUpload}
<dialog class="modal modal-open">
	<div class="modal-box max-w-3xl">
		<h3 class="font-bold text-lg mb-2">{selectedUpload.filename}</h3>
		<p class="text-sm opacity-70 mb-4">
			Type: <span class="uppercase">{selectedUpload.file_type}</span> • Uploaded: {new Date(selectedUpload.upload_date).toLocaleString()} • Parsed: {selectedUpload.campaign_count}
		</p>
		<div class="space-y-3 max-h-96 overflow-y-auto">
			{#if selectedUpload.parsed_campaigns?.length}
				{#each selectedUpload.parsed_campaigns as pc, i}
					<div class="card bg-base-200">
						<div class="card-body">
							<h4 class="card-title">{i + 1}. {pc.title}</h4>
							<p class="whitespace-pre-wrap">{pc.content?.slice(0, 200)}{pc.content && pc.content.length > 200 ? '…' : ''}</p>
						</div>
					</div>
				{/each}
			{:else}
				<p class="opacity-70">No parsed campaigns found.</p>
			{/if}
		</div>
		<div class="modal-action">
			<button class="btn" onclick={() => { showUploadModal = false; selectedUpload = null; }}>Close</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button onclick={() => { showUploadModal = false; selectedUpload = null; }}>close</button>
	</form>
</dialog>
{/if}
