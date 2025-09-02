<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';

    type Guideline = {
        id: number;
        title: string;
        content: string;
        guideline_type: string;
        uploaded_at: string;
    };

    let guidelines: Guideline[] = $state([]);
    let loading: boolean = $state(true);
    let errorMessage: string | null | undefined = $state();

    async function loadGuidelines() {
        loading = true;
        errorMessage = null;
        try {
            const response = await fetch('api/brand-guidelines/', {
                headers: { Accept: 'application/json' },
                credentials: 'include'
            });

            if (!response.ok) {
                if (response.status === 401) return goto('/login');
                errorMessage = response.statusText;
                loading = false;
                return;
            }

            const data: Guideline[] = await response.json();
            guidelines = data ?? [];
            loading = false;
        } catch (err) {
            console.error(err);
            errorMessage = 'Failed to load guidelines';
            loading = false;
        }
    }

    onMount(loadGuidelines);
</script>

<div class="p-6">
    <div class="mb-6 flex items-center justify-between">
        <h1 class="text-3xl font-semibold">Brand Guidelines</h1>
        <button class="btn btn-neutral" onclick={loadGuidelines} disabled={loading}>
            {#if loading}
                <span class="loading loading-spinner loading-sm"></span>
                Refreshing
            {:else}
                Refresh
            {/if}
        </button>
    </div>

    {#if errorMessage}
        <div role="alert" class="alert alert-error mb-4">
            <button type="button" aria-label="close alert" onclick={() => (errorMessage = null)}>
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 shrink-0 stroke-current" fill="none" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
            </button>
            <span>{errorMessage}</span>
        </div>
    {/if}

    {#if loading}
        <div class="flex items-center justify-center p-8">
            <span class="loading loading-spinner loading-lg"></span>
        </div>
    {:else if guidelines.length === 0}
        <div class="card bg-base-200">
            <div class="card-body">
                <h2 class="card-title">No guidelines yet</h2>
                <p>Once you create brand guidelines, they will appear here.</p>
            </div>
        </div>
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
                    {#each guidelines as g}
                        <tr>
                            <td class="font-medium">{g.title}</td>
                            <td class="uppercase text-xs opacity-70">{g.guideline_type}</td>
                            <td>{new Date(g.uploaded_at).toLocaleString()}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</div>


