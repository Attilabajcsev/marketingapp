<script lang="ts">
	import { goto } from '$app/navigation';
</script>

<div class="hero bg-base-200 min-h-[95vh]">
	<div class="flex-col">
		<div class="mb-10 text-center lg:text-left">
			<h1 class="text-5xl font-bold">Sign-up now!</h1>
		</div>
		<div class="card bg-base-100 w-full max-w-sm min-w-sm shrink-0 shadow-2xl">
			<div class="card-body">
				<form method="post" action="?/register">
					<fieldset class="fieldset">
						<label for="email" class="label">Email</label>
						<input
							required
							type="email"
							name="email"
							id="email"
							class="input"
							placeholder="Email address"
						/>
						<label for="first_name" class="label">First Name</label>
						<input
							required
							type="text"
							name="first_name"
							id="first_name"
							class="input"
							placeholder="First Name"
						/>
						<label for="last_name" class="label">Last Name</label>
						<input
							required
							type="text"
							name="last_name"
							id="last_name"
							class="input"
							placeholder="Last Name"
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
						<button type="submit" class="btn btn-neutral mt-4"> Sign-up </button>
						<button type="button" class="btn" onclick={() => goto('/')}> Back </button>
					</fieldset>
				</form>
			</div>
		</div>
	</div>
</div>
