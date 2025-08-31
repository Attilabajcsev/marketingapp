import { redirect } from '@sveltejs/kit';
import type { Actions, RequestEvent } from '@sveltejs/kit';
import * as api from '$lib/api.js';

export async function load({ locals }) {
	if (locals.authed) {
		redirect(303, '/main');
	}
}

export const actions: Actions = {
	login: async ({ cookies, request }: RequestEvent) => {
		const loginFormData = await request.formData();
		const username = loginFormData.get('username')?.toString() ?? '';
		const password = loginFormData.get('password')?.toString() ?? '';

		const data: { access: string; refresh: string } = await api.post('login/', {
			username,
			password
		});
		const accessToken = data.access;
		const refreshToken = data.refresh;

		cookies.set('accessToken', accessToken, {
			httpOnly: true,
			path: '/',
			maxAge: 60 * 60,
			sameSite: 'lax'
		}); //expires in 1h

		cookies.set('refreshToken', refreshToken, {
			httpOnly: true,
			path: '/',
			maxAge: 60 * 60 * 24 * 7,
			sameSite: 'lax'
		}); // expires in 1 week

		console.log('login successful. Redirecting..');
		redirect(303, '/main');
	}
};
