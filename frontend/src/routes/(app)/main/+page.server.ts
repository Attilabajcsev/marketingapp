import type { PageServerLoad } from '/$types';
import { redirect } from '@sveltejs/kit';
import type { UserData } from '$lib/types';
import type { Actions, RequestEvent } from '@sveltejs/kit';
import * as api from '$lib/api.js';

export const load: PageServerLoad = async (event: RequestEvent): Promise<UserData> => {
	const token = event.cookies.get('accessToken');
	if (!token || !event.locals.authed) {
		throw redirect(303, '/login');
	}

	return await api.get('user/profile/', token);
};

export const actions: Actions = {
	getUserData: async (event: RequestEvent) => {
		const token = event.cookies.get('accessToken');
		if (!token || !event.locals.authed) {
			throw redirect(303, '/login');
		}

		return await api.get('user/profile/', token);
	}
};
