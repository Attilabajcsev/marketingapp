<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';

	let { data, children } = $props();
	let nonProtectedRoutes: string[] = ['/', '/login', '/register', '/login-oauth', '/oauth-google'];
</script>

<div class="flex min-h-screen flex-col">
	<div class="navbar bg-base-100 border-base-300 border shadow-md">
		<div class="navbar-start">
			<a class="btn btn-ghost text-xl" href="/main">Email Assistant</a>
		</div>
		<div class="navbar-center hidden lg:flex"></div>
		<div class="navbar-end">
			{#if !nonProtectedRoutes.includes(page?.url.pathname)}
				<div class="dropdown dropdown-end">
					<div tabindex="0" role="button" class="btn btn-ghost">
						<p class="text-md mr-4">{data.user.email}</p>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="h-5 w-5"
							fill="none"
							viewBox="0 0 24 24"
							stroke="currentColor"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 6h16M4 12h8m-8 6h16"
							/>
						</svg>
					</div>
					<ul
						tabindex="0"
						class="menu menu-md dropdown-content bg-base-100 rounded-box z-1 mt-3 w-52 p-2 shadow"
					>
						<li><a href="/main">Home</a></li>
						<li><a href="/logout" data-sveltekit-preload-data="off">Logout</a></li>
					</ul>
				</div>
			{/if}
		</div>
	</div>

	<div class="flex-1">
		{@render children()}
	</div>

	<footer class="footer sm:footer-horizontal footer-center bg-base-300 text-base-content p-4">
		<aside>
			<p>Copyright © {new Date().getFullYear()} - Email Assistant</p>
		</aside>
	</footer>
</div>
