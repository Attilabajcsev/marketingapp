import { redirect } from '@sveltejs/kit';
import { error } from '@sveltejs/kit';
import * as api from '$lib/api';
import type { RequestEvent } from './routes/$types';
import type { UserData } from '$lib/types';

const VERIFY_URL = 'token/verify/';
const REFRESH_URL = 'token/refresh/';
const userCache = new Map();
const TTL = 6 * 60 * 60 * 1000;

export async function handle({ event, resolve }) {
	let accessToken = event.cookies.get('accessToken');
	const refreshToken = event.cookies.get('refreshToken');

	if (accessToken) {
		try {
			await api.post(VERIFY_URL, { token: accessToken });
			event.locals.authed = true;
		} catch (error) {
			if (refreshToken) {
				try {
					const refreshResponse = await api.post(REFRESH_URL, { refresh: refreshToken });

					if (refreshResponse.access) {
						event.cookies.set('accessToken', refreshResponse.access, {
							httpOnly: true,
							path: '/',
							maxAge: 60 * 60,
							sameSite: 'lax'
						});
						event.locals.authed = true;
						accessToken = refreshResponse.access;
					} else clearCookies(<RequestEvent>event);
				} catch (refreshError) {
					clearCookies(<RequestEvent>event);
					console.log(`Failed to refresh token ${refreshError}`);
				}
			} else {
				clearCookies(<RequestEvent>event);
				console.log(`Failed to refresh token ${error}`);
			}
		}
	} else clearCookies(<RequestEvent>event);

	// Protect routes that require authentication

	const publicRoutes = ['/', '/login', '/register', '/login-oauth', '/oauth-google'];
	const isPublicRoute = publicRoutes.includes(event.url.pathname);

	if (!isPublicRoute) {
		if (!event.locals.authed) redirect(302, '/');

		try {
			if (!accessToken) error(401, 'Unauthorized');
			event.locals.UserData = await getUserData(accessToken);
		} catch (err) {
			clearCookies(<RequestEvent>event);
			error(500, `Unable to load user profile ${err}`);
		}
	}

	return await resolve(event);
}

// Supporting functions
function clearCookies(event: RequestEvent): void {
	const token = event.cookies.get('accessToken');
	if (token) userCache.delete(token);
	event.cookies.delete('accessToken', { path: '/' });
	event.cookies.delete('refreshToken', { path: '/' });
}

async function getUserData(accessToken: string): Promise<UserData> {
	const cachedUser: { data: UserData; timestamp: number } = userCache.get(accessToken);

	console.log('looking for user cache');
	if (cachedUser && Date.now() - cachedUser.timestamp < TTL) return cachedUser.data;

	console.log('no cache, fetching new data');
	try {
		const data: UserData = await api.get('user/profile/', accessToken);
		userCache.set(accessToken, {
			data,
			timestamp: Date.now()
		});

		return data;
	} catch (err) {
		console.log(`Failed to fetch user ${err}`);
		error(500, `Failed to fetch user ${err}`);
	}
}
