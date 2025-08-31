import { redirect } from '@sveltejs/kit';

export function load({ cookies }) {
	cookies.delete('accessToken', { path: '/' });
	cookies.delete('refreshToken', { path: '/' });
	redirect(302, '/');
}
