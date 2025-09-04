import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';
import { json } from '@sveltejs/kit';

const BACKEND_URL = env.BACKEND_URL;

export const GET: RequestHandler = async ({ request, cookies, params }) => {
	const token = cookies.get('accessToken');
	const path = params.path;
	const normalized = path.endsWith('/') ? path : `${path}/`;
	const url = `${BACKEND_URL}/${normalized}`;
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
	const token = cookies.get('accessToken');
	const path = params.path;
	const normalized = path.endsWith('/') ? path : `${path}/`;
	const url = `${BACKEND_URL}/${normalized}`;

	const headers = new Headers();
	if (token) headers.set('Authorization', `Bearer ${token}`);
	const accept = request.headers.get('accept');
	if (accept) headers.set('accept', accept);

	let body: BodyInit | undefined;
	const contentType = request.headers.get('content-type') || '';
	if (contentType.startsWith('application/json')) {
		const jsonBody = await request.json();
		headers.set('content-type', 'application/json');
		body = JSON.stringify(jsonBody);
	} else if (contentType.startsWith('multipart/form-data')) {
		const form = await request.formData();
		body = form as unknown as BodyInit;
	} else {
		body = request.body as BodyInit;
	}

	const response = await fetch(url, {
		method: 'POST',
		headers,
		body
	});

	if (!response.ok) return json({ error: response.statusText }, { status: response.status });

	const responseJSON = await response.json();
	return json(responseJSON, { status: 200 });
};

export const PUT: RequestHandler = async ({ request, cookies, params }) => {
	const token = cookies.get('accessToken');
	const path = params.path;
	const normalized = path.endsWith('/') ? path : `${path}/`;
	const url = `${BACKEND_URL}/${normalized}`;

	const headers = new Headers();
	if (token) headers.set('Authorization', `Bearer ${token}`);
	const accept = request.headers.get('accept');
	if (accept) headers.set('accept', accept);

	let body: BodyInit | undefined;
	const contentType = request.headers.get('content-type') || '';
	if (contentType.startsWith('application/json')) {
		const jsonBody = await request.json();
		headers.set('content-type', 'application/json');
		body = JSON.stringify(jsonBody);
	} else if (contentType.startsWith('multipart/form-data')) {
		const form = await request.formData();
		body = form as unknown as BodyInit;
	} else {
		body = request.body as BodyInit;
	}

	const response = await fetch(url, {
		method: 'PUT',
		headers,
		body
	});

	if (!response.ok) return json({ error: response.statusText }, { status: response.status });

	const responseJSON = await response.json();
	return json(responseJSON, { status: 200 });
};

export const DELETE: RequestHandler = async ({ request, cookies, params }) => {
	const token = cookies.get('accessToken');
	const path = params.path;
	const normalized = path.endsWith('/') ? path : `${path}/`;
	const url = `${BACKEND_URL}/${normalized}`;
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
