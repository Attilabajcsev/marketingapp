<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
</script>

<div class="hero bg-base-200 min-h-[95vh]">
	<div class="flex-col">
		<div class="mb-10 text-center lg:text-left">
			<h1 class="text-5xl font-bold">Login now!</h1>
		</div>
		<div class="card bg-base-100 w-full max-w-sm min-w-sm shrink-0 shadow-2xl">
			<div class="card-body">
				<form action="?/login" method="post" use:enhance>
					<fieldset class="fieldset">
						<label for="email" class="label">Email</label>
						<input
							required
							type="email"
							name="username"
							id="username"
							class="input"
							placeholder="Email address"
						/>
						<label for="password" class="label">Password</label>
						<input
							required
							type="password"
							class="input"
							name="password"
							id="password"
							placeholder="Password"
						/>
						<div><a class="link link-hover" href="/">Forgot password?</a></div>
						<button type="submit" class="btn btn-neutral mt-4"> Login </button>
						<button type="button" class="btn" onclick={() => goto('/')}> Back </button>
					</fieldset>
				</form>
			</div>
		</div>
	</div>
</div>
