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

	// Prompt and output state
	let userPrompt: string = $state('');
	let outputText: string = $state('');
	let generating: boolean = $state(false);
	let copySuccess: boolean = $state(false);
	let hasOutput: boolean = $derived(!!outputText && outputText.trim().length > 0);
	let linkedinUrl: string = $state('');
	let linkedinLoading: boolean = $state(false);
	let linkedinLoaded: boolean = $state(false);
	let usedLinkedIn: boolean = $state(false);
	let linkedinError: string = $state('');
	let websiteUrl: string = $state('');
	let websiteLoading: boolean = $state(false);
	let websiteLoaded: boolean = $state(false);
	let websiteError: string = $state('');
	let showLinkedinPreview: boolean = $state(false);
	let linkedinPreview: string = $state('');
	let linkedinFull: string = $state('');
	let showWebsitePreview: boolean = $state(false);
	let websitePreviewAll: string[] = $state([]);
	let showContextAudit: boolean = $state(false);
	let auditData: { brand_guidelines?: any; prompt_messages?: any; rag_uploads_examples?: any[]; rag_websites_examples?: any[] } = $state({});
	let ragUploadsExamples: { chunk_id: number; source_type: string; source_id: number; text: string }[] = $state([]);
	let ragWebsitesExamples: { chunk_id: number; source_type: string; source_id: number; text: string }[] = $state([]);

	async function copyOutput() {
		if (!hasOutput) return;
		try {
			await navigator.clipboard.writeText(outputText);
			copySuccess = true;
			setTimeout(() => (copySuccess = false), 1500);
		} catch (e) {
			console.error(e);
		}
	}

	function downloadOutput() {
		if (!hasOutput) return;
		try {
			const blob = new Blob([outputText], { type: 'text/plain;charset=utf-8' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'generated-content.txt';
			document.body.appendChild(a);
			a.click();
			a.remove();
			URL.revokeObjectURL(url);
		} catch (e) {
			console.error(e);
		}
	}

	// Vector search state
	type SearchItem = { id: number; text: string; source_type: string; source_id: number };
	let searchQuery: string = $state('');
	let searchLoading: boolean = $state(false);
	let searchResults: SearchItem[] = $state([]);

	async function runSearch() {
		if (!searchQuery.trim()) return;
		searchLoading = true;
		try {
			const res = await fetch('api/vectorstore/search/', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ query: searchQuery.trim(), top_k: 5 })
			});
			if (!res.ok) {
				searchResults = [];
				return;
			}
			const data = await res.json();
			searchResults = data.results ?? [];
		} catch (e) {
			console.error(e);
			searchResults = [];
		} finally {
			searchLoading = false;
		}
	}

	// Chat (LLM) state
	let chatPrompt: string = $state('');
	let chatLoading: boolean = $state(false);
	let chatReply: string = $state('');

	async function runChat() {
		if (!chatPrompt.trim()) return;
		chatLoading = true;
		chatReply = '';
		try {
			const res = await fetch('api/vectorstore/chat/', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ prompt: chatPrompt.trim() })
			});
			if (!res.ok) {
				chatReply = 'Error calling chat endpoint';
				return;
			}
			const data = await res.json();
			chatReply = data.reply ?? '';
		} catch (e) {
			console.error(e);
			chatReply = 'Error calling chat endpoint';
		} finally {
			chatLoading = false;
		}
	}

	// Simple tabbed layout to declutter the page
	let activeTab: 'guidelines' | 'uploads' | 'search' | 'chat' = $state('guidelines');

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

	// Minimal guideline preview modal state
	let showGuidelineModal: boolean = $state(false);
	let selectedGuideline: Campaign | null = $state(null);

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

	function openGuideline(c: Campaign) {
		selectedGuideline = c;
		showGuidelineModal = true;
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

	async function generate() {
		const prompt = userPrompt.trim();
		if (!prompt) return;
		generating = true;
		outputText = '';
		try {
			const res = await fetch('api/vectorstore/generate/', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ prompt, top_k: 5 })
			});
			if (!res.ok) {
				outputText = 'Error generating content.';
				return;
			}
			const data = await res.json();
			outputText = data.reply ?? '';
			usedLinkedIn = Boolean(data.used_linkedin);
			// update previews from generation response if available
			if (!linkedinPreview && data.linkedin_context_preview) {
				linkedinPreview = String(data.linkedin_context_preview);
			}
			ragUploadsExamples = Array.isArray(data.rag_uploads_examples) ? data.rag_uploads_examples : [];
			ragWebsitesExamples = Array.isArray(data.rag_websites_examples) ? data.rag_websites_examples : [];
			auditData = {
				brand_guidelines: data.brand_guidelines,
				prompt_messages: data.prompt_messages,
				rag_uploads_examples: ragUploadsExamples,
				rag_websites_examples: ragWebsitesExamples
			};
		} catch (e) {
			console.error(e);
			outputText = 'Error generating content.';
		} finally {
			generating = false;
		}
	}

	async function scanLinkedIn() {
		const url = linkedinUrl.trim();
		if (!url) return;
		linkedinLoading = true;
		linkedinLoaded = false;
		linkedinError = '';
		try {
			const res = await fetch('api/linkedin/scrape/', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url })
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				linkedinError = String(err?.error || 'Failed to fetch LinkedIn content');
				return;
			}
			const data = await res.json();
			linkedinFull = String(data?.content || '');
			linkedinPreview = linkedinFull ? linkedinFull : String((data && data.preview_texts && data.preview_texts[0]) || '');
			linkedinLoaded = true;
		} catch (e) {
			console.error(e);
			linkedinError = 'Failed to fetch LinkedIn content';
		} finally {
			linkedinLoading = false;
		}
	}

	async function scanWebsite() {
		const url = websiteUrl.trim();
		if (!url) return;
		websiteLoading = true;
		websiteError = '';
		try {
			const res = await fetch('api/website/scrape/', {
				method: 'POST',
				credentials: 'include',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ url })
			});
			const data = await res.json().catch(() => ({}));
			if (!res.ok) {
				websiteError = String(data?.error || 'Failed to fetch website content');
				return;
			}
			if (data?.error) {
				websiteError = String(data.error);
			}
			// Prefer full posts if provided
			if (Array.isArray(data?.preview_posts_full) && data.preview_posts_full.length) {
				websitePreviewAll = data.preview_posts_full.map((p: any) => `${p.title || 'Untitled'}\n\n${p.text || ''}`);
			} else {
				websitePreviewAll = Array.isArray(data?.preview_texts) ? data.preview_texts : [];
			}
			websiteLoaded = true;
		} catch (e) {
			console.error(e);
			websiteError = 'Failed to fetch website content';
		} finally {
			websiteLoading = false;
		}
	}

	// Load any previously saved scrapes so view buttons persist after refresh
	async function loadSavedSources() {
		try {
			// LinkedIn
			const li = await fetch('api/linkedin/scrape/', { credentials: 'include' });
			if (li.ok) {
				const data = await li.json();
				linkedinFull = String(data?.content || '');
				linkedinPreview = linkedinFull ? linkedinFull : String((data && data.preview_texts && data.preview_texts[0]) || '');
				linkedinLoaded = true;
				if (data?.url) linkedinUrl = data.url;
			}
		} catch {}
		try {
			// Website
			const wb = await fetch('api/website/scrape/', { credentials: 'include' });
			if (wb.ok) {
				const data = await wb.json();
				if (Array.isArray(data?.preview_posts_full) && data.preview_posts_full.length) {
					websitePreviewAll = data.preview_posts_full.map((p: any) => `${p.title || 'Untitled'}\n\n${p.text || ''}`);
				} else {
					websitePreviewAll = Array.isArray(data?.preview_texts) ? data.preview_texts : [];
				}
				websiteLoaded = true;
				if (data?.url) websiteUrl = data.url;
			}
		} catch {}
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
	onMount(loadSavedSources);
</script>

<div class="min-h-screen bg-white p-6">
	<div class="mx-auto max-w-[1800px]">
		<div class="grid grid-cols-1 gap-6 items-stretch lg:grid-cols-[560px_1120px]">
			<!-- LEFT COLUMN: Your Sources -->
			<div class="space-y-4">
				<div class="rounded-md border border-gray-200 bg-white p-4">
					<h2 class="mb-1 text-lg font-semibold">Your Sources</h2>
					<p class="text-sm text-gray-500">Add sources to inform generation.</p>
				</div>


				<!-- Links card (compact) -->
				<div class="rounded-md border border-gray-200 bg-white p-4">
					<div class="mb-2 flex items-center justify-between">
						<h3 class="font-medium">Links</h3>
					</div>
					<div class="space-y-2">
						<div class="flex gap-2">
							<input class="input input-bordered w-full" type="url" placeholder="www.example.com/blog" bind:value={websiteUrl} />
							<button class="btn btn-neutral" onclick={scanWebsite} disabled={websiteLoading || !websiteUrl}>
								{#if websiteLoading}
									<span class="loading loading-spinner loading-sm"></span>
									Scanning
								{:else}
									Scan Website
								{/if}
							</button>
						</div>
						{#if websiteError}
							<p class="text-xs text-red-600">{websiteError}</p>
						{/if}
						<div class="flex gap-2">
							<input class="input input-bordered w-full" type="url" placeholder="www.linkedin.com/company/example" bind:value={linkedinUrl} />
							<button class="btn btn-neutral" onclick={scanLinkedIn} disabled={linkedinLoading || !linkedinUrl}>
								{#if linkedinLoading}
									<span class="loading loading-spinner loading-sm"></span>
									Scanning
								{:else}
									Scan LinkedIn
								{/if}
							</button>
						</div>
						{#if linkedinError}
							<p class="text-xs text-red-600">{linkedinError}</p>
						{/if}
						<div class="flex items-center gap-2">
							{#if linkedinLoaded}
								<button class="btn btn-xs" onclick={() => (showLinkedinPreview = true)}>View LinkedIn</button>
							{/if}
							{#if websiteUrl}
								<button class="btn btn-xs" onclick={() => (showWebsitePreview = true)}>View Website</button>
							{/if}
						</div>
					</div>
				</div>

				<!-- Upload Old Content card -->
				<div class="rounded-md border border-gray-200 bg-white p-4">
					<div class="mb-2 flex items-center justify-between">
						<h3 class="font-medium">Upload Old Content</h3>
						<span class="text-sm {uploads.length > 0 ? 'text-green-600' : 'text-gray-500'}">
							{uploads.length > 0 ? `✓ ${uploads.length} items loaded` : 'No data yet'}
						</span>
					</div>
					<div class="flex items-center gap-2">
						<input class="file-input file-input-bordered w-full" type="file" accept=".csv,.txt,.json" onchange={(e: Event) => { const t = e.target as HTMLInputElement; fileToUpload = (t.files && t.files[0]) || null; }} />
						<button class="btn btn-neutral" onclick={uploadFile} disabled={uploadBusy || !fileToUpload}>
							{#if uploadBusy}
								<span class="loading loading-spinner loading-sm"></span>
								Uploading
							{:else}
								Upload
							{/if}
						</button>
					</div>
					{#if uploadsLoading}
						<p class="mt-2 text-sm text-gray-500">Loading uploads…</p>
					{/if}
					{#if uploads.length > 0}
						<div class="mt-2 space-y-1">
							{#each uploads.slice(0, 3) as u}
								<div class="flex items-center justify-between rounded border border-gray-200 p-2">
									<p class="text-sm">{u.filename}</p>
									<button class="btn btn-xs" onclick={() => openUploadDetail(u.id)}>View</button>
								</div>
							{/each}
							{#if uploads.length > 3}
								<p class="text-xs text-gray-500">and {uploads.length - 3} more…</p>
							{/if}
						</div>
					{/if}
				</div>

				<!-- Brand Guidelines card -->
				<div class="rounded-md border border-gray-200 bg-white p-4">
					<div class="mb-2 flex items-center justify-between">
						<h3 class="font-medium">Brand Guidelines</h3>
						<span class="text-sm {campaigns.length > 0 ? 'text-green-600' : 'text-gray-500'}">
							{campaigns.length > 0 ? `✓ ${campaigns.length} items loaded` : 'No data yet'}
						</span>
					</div>
					<div class="space-y-2">
						<input class="input input-bordered w-full" type="text" placeholder="Guideline title" bind:value={newTitle} />
						<select class="select select-bordered w-full" bind:value={newType}>
							<option value="tone">Tone of Voice</option>
							<option value="terminology">Company Terminology</option>
							<option value="style">Writing Style</option>
							<option value="rules">Content Rules</option>
						</select>
						<textarea class="textarea textarea-bordered w-full min-h-24" placeholder="Guideline content" bind:value={newContent} />
						<div class="flex justify-end">
							<button class="btn btn-neutral" onclick={createCampaign} disabled={createLoading}>
								{#if createLoading}
									<span class="loading loading-spinner loading-sm"></span>
									Add
								{:else}
									Add
								{/if}
							</button>
						</div>
					</div>
					{#if campaignsLoading}
						<p class="mt-2 text-sm text-gray-500">Loading guidelines…</p>
					{:else if campaigns.length > 0}
						<div class="mt-3 space-y-1">
							{#each campaigns.slice(0, 3) as c}
								<div class="flex items-center justify-between rounded border border-gray-200 p-2">
									<div>
										<p class="text-sm font-medium">{c.title}</p>
										<p class="text-xs text-gray-500">{c.guideline_type} • {new Date(c.uploaded_at).toLocaleDateString()}</p>
									</div>
									<button class="btn btn-xs" onclick={() => openGuideline(c)}>View</button>
								</div>
							{/each}
							{#if campaigns.length > 3}
								<p class="text-xs text-gray-500">and {campaigns.length - 3} more…</p>
							{/if}
						</div>
					{/if}
				</div>
			</div>

			<!-- RIGHT COLUMN: Prompt and Output -->
			<div class="flex flex-col gap-4 h-full">
				<div class="rounded-md border border-gray-200 bg-white p-4 flex flex-col flex-1">
					<h2 class="mb-2 text-lg font-semibold">Write your prompt:</h2>
					<textarea class="textarea textarea-bordered w-full flex-1 min-h-0" placeholder="Describe what you want to generate…" bind:value={userPrompt} />
					<div class="mt-2 flex justify-end">
						<button class="btn btn-neutral" onclick={generate} disabled={generating}>
							{#if generating}
								<span class="loading loading-spinner loading-sm"></span>
								Generating
							{:else}
								Generate
							{/if}
						</button>
					</div>
				</div>

				<div class="rounded-md border border-gray-200 bg-white p-4 flex flex-col flex-1">
					<h2 class="mb-2 text-lg font-semibold">Your generated content</h2>
					<textarea class="textarea textarea-bordered w-full flex-1 min-h-0" placeholder="Output will appear here…" bind:value={outputText} readonly />
					<div class="mt-2 flex items-center justify-end gap-2">
						{#if copySuccess}
							<span class="text-xs text-green-600">Copied!</span>
						{/if}
						<button class="btn" onclick={copyOutput} disabled={!hasOutput}>Copy</button>
						<button class="btn" onclick={downloadOutput} disabled={!hasOutput}>Download</button>
						{#if hasOutput && (usedLinkedIn || (auditData?.similar_examples && auditData.similar_examples.length))}
							<button class="btn" onclick={() => (showContextAudit = true)}>Used context</button>
						{/if}
					</div>
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
					<div class="rounded-md border border-gray-200 bg-white p-3">
						<p class="text-sm font-medium">{i + 1}. {pc.title}</p>
						<p class="text-sm text-gray-600 whitespace-pre-wrap">{pc.content}</p>
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

{#if showGuidelineModal && selectedGuideline}
<dialog class="modal modal-open">
	<div class="modal-box max-w-2xl">
		<h3 class="font-bold text-lg mb-2">{selectedGuideline.title}</h3>
		<p class="text-sm opacity-70 mb-4">Type: {selectedGuideline.guideline_type} • {new Date(selectedGuideline.uploaded_at).toLocaleDateString()}</p>
		<div class="max-h-96 overflow-y-auto">
			<p class="whitespace-pre-wrap text-sm">{selectedGuideline.content}</p>
		</div>
		<div class="modal-action">
			<button class="btn" onclick={() => { showGuidelineModal = false; selectedGuideline = null; }}>Close</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button onclick={() => { showGuidelineModal = false; selectedGuideline = null; }}>close</button>
	</form>
</dialog>
{/if}

{#if showLinkedinPreview && linkedinLoaded}
<dialog class="modal modal-open">
	<div class="modal-box max-w-3xl">
		<h3 class="font-bold text-lg mb-2">LinkedIn context preview</h3>
		<div class="mb-3 flex items-center gap-2 text-xs opacity-70">
			<span>{linkedinUrl}</span>
			{#if linkedinFull}
				<span>({linkedinFull.length} chars)</span>
			{/if}
		</div>
		<div class="max-h-[70vh] overflow-y-auto">
			<p class="whitespace-pre-wrap text-sm">{linkedinFull || linkedinPreview || 'No preview available.'}</p>
		</div>
		<div class="modal-action">
			<button class="btn" onclick={() => (showLinkedinPreview = false)}>Close</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button onclick={() => (showLinkedinPreview = false)}>close</button>
	</form>
</dialog>
{/if}

{#if showWebsitePreview}
<dialog class="modal modal-open">
	<div class="modal-box max-w-3xl">
		<h3 class="font-bold text-lg mb-2">Website blog preview</h3>
		<div class="max-h-96 overflow-y-auto space-y-2">
			{#if websitePreviewAll?.length}
				{#each websitePreviewAll as t, i}
					<div class="rounded-md border border-gray-200 bg-white p-3">
						<p class="text-xs opacity-70 mb-1">Excerpt {i + 1}</p>
						<p class="whitespace-pre-wrap text-sm">{t}</p>
					</div>
				{/each}
			{:else}
				<p class="opacity-70">No preview available.</p>
			{/if}
		</div>
		<div class="modal-action">
			<button class="btn" onclick={() => (showWebsitePreview = false)}>Close</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button onclick={() => (showWebsitePreview = false)}>close</button>
	</form>
</dialog>
{/if}

{#if showContextAudit}
<dialog class="modal modal-open">
	<div class="modal-box max-w-4xl">
		<h3 class="font-bold text-lg mb-2">Used context & prompt</h3>
		<div class="max-h-[70vh] overflow-y-auto space-y-4">
			<div>
				<h4 class="font-semibold mb-1">Brand Guidelines</h4>
				<pre class="whitespace-pre-wrap text-sm bg-base-200 p-2 rounded">{JSON.stringify(auditData.brand_guidelines, null, 2)}</pre>
			</div>
			<div>
				<h4 class="font-semibold mb-1">Uploads (RAG)</h4>
				<pre class="whitespace-pre-wrap text-sm bg-base-200 p-2 rounded">{JSON.stringify(auditData.rag_uploads_examples, null, 2)}</pre>
			</div>
			<div>
				<h4 class="font-semibold mb-1">Blogs (RAG)</h4>
				<pre class="whitespace-pre-wrap text-sm bg-base-200 p-2 rounded">{JSON.stringify(auditData.rag_websites_examples, null, 2)}</pre>
			</div>
			<div>
				<h4 class="font-semibold mb-1">Prompt Template Messages</h4>
				<pre class="whitespace-pre-wrap text-sm bg-base-200 p-2 rounded">{JSON.stringify(auditData.prompt_messages, null, 2)}</pre>
			</div>
		</div>
		<div class="modal-action">
			<button class="btn" onclick={() => (showContextAudit = false)}>Close</button>
		</div>
	</div>
	<form method="dialog" class="modal-backdrop">
		<button onclick={() => (showContextAudit = false)}>close</button>
	</form>
</dialog>
{/if}
