import { redirect } from '@sveltejs/kit';
import type { RequestEvent } from './$types.js';
import * as api from '$lib/api.js';

export async function load({ locals }) {
	if (locals.authed) {
		redirect(303, '/main');
	}
}

export const actions = {
	register: async (event: RequestEvent) => {
		const loginFormData = await event.request.formData();
		const email = loginFormData.get('email');
		const first_name = loginFormData.get('first_name');
		const last_name = loginFormData.get('last_name');
		const username = loginFormData.get('email');
		const password = loginFormData.get('password');

		await api.post('register/', {
			email,
			first_name,
			last_name,
			username,
			password
		});

		redirect(303, '/main');
	}
};
