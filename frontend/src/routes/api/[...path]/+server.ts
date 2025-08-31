import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';
import { json } from '@sveltejs/kit';

const BACKEND_URL = env.BACKEND_URL;

export const GET: RequestHandler = async ({ request, cookies, params }) => {
	const token = cookies.get('accessToken');
	const path = params.path;
	const url = `${BACKEND_URL}/${path}`;
	const headers = request.headers;

	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}

	const response = await fetch(url, {
		method: 'GET',
		headers
	});
	const responseJSON = await response.json();
	if (!response.ok) return json({ error: response.statusText }, { status: response.status });
	return json(responseJSON, { status: 200 });
};

export const POST: RequestHandler = async ({ request, cookies, params }) => {
	const body = await request.json();
	const token = cookies.get('accessToken');
	const path = params.path;
	const url = `${BACKEND_URL}/${path}`;
	const headers = request.headers;

	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}

	const response = await fetch(url, {
		method: request.method,
		headers,
		body: JSON.stringify(body)
	});

	if (!response.ok) return json({ error: response.statusText }, { status: response.status });

	return json(response, { status: 200 });
};

export const DELETE: RequestHandler = async ({ request, cookies, params }) => {
	const token = cookies.get('accessToken');
	const path = params.path;
	const url = `${BACKEND_URL}/${path}`;
	const headers = request.headers;

	if (token) {
		headers.set('Authorization', `Bearer ${token}`);
	}

	const response = await fetch(url, {
		method: request.method,
		headers
	});

	if (!response.ok) return json({ error: response.statusText }, { status: response.status });

	return json(response, { status: 200 });
};
