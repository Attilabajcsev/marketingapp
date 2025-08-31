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
				<form action="?/OAuth2" method="post" use:enhance>
					<fieldset class="fieldset">
						<button type="submit" class="btn border-[#e5e5e5] bg-white text-black">
							<svg
								aria-label="Google logo"
								width="16"
								height="16"
								xmlns="http://www.w3.org/2000/svg"
								viewBox="0 0 512 512"
								><g
									><path d="m0 0H512V512H0" fill="#fff"></path><path
										fill="#34a853"
										d="M153 292c30 82 118 95 171 60h62v48A192 192 0 0190 341"
									></path><path
										fill="#4285f4"
										d="m386 400a140 175 0 0053-179H260v74h102q-7 37-38 57"
									></path><path fill="#fbbc02" d="m90 341a208 200 0 010-171l63 49q-12 37 0 73"
									></path><path
										fill="#ea4335"
										d="m153 219c22-69 116-109 179-50l55-54c-78-75-230-72-297 55"
									></path></g
								></svg
							>
							Login with Google
						</button>

						<button type="button" class="btn" onclick={() => goto('/')}> Back </button>
					</fieldset>
				</form>
			</div>
		</div>
	</div>
</div>
