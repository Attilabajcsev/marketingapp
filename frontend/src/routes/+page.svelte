<script>
	import { goto } from '$app/navigation';
</script>

<div class="hero bg-base-200 min-h-[90vh]">
	<div class="hero-content text-center">
		<div class="max-w-md">
			<h1 class="text-5xl font-bold">Hello there!</h1>
			<p class="py-6">
				This is a SvelteKit application working together with a Django REST backend.
			</p>
			<div class="flex flex-col items-center justify-center gap-4">
				<button class="btn btn-neutral w-50" onclick={() => goto('/login-oauth')}
					>Login with Google</button
				>
				<button class="btn btn-neutral w-50" onclick={() => goto('/login')}>Login</button>
				<button class="btn btn-neutral w-50" onclick={() => goto('/register')}>Sign-up</button>
			</div>
		</div>
	</div>
</div>
