import { redirect } from '@sveltejs/kit';

export async function load({ locals }) {
	if (locals.authed) {
		redirect(303, '/main');
	}
}
