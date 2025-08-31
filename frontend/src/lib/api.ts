import { error } from '@sveltejs/kit';
import type { ApiOptions } from './types';
import { env } from '$env/dynamic/private';

const base = env.BACKEND_URL;

async function send({
	method,
	path,
	data,
	token
}: {
	method: string;
	path: string;
	data?: object;
	token?: string;
}) {
	const opts: ApiOptions = { method, headers: {} };

	if (data) {
		opts.headers['Content-Type'] = 'application/json';
		opts.body = JSON.stringify(data);
	}

	if (token) {
		opts.headers['Authorization'] = `Bearer ${token}`;
	}

	const res = await fetch(`${base}/${path}`, opts);

	if (res.ok || res.status === 422) {
		const text = await res.text();
		return text ? JSON.parse(text) : {};
	}

	error(res.status);
}

export function get(path: string, token?: string) {
	return send({ method: 'GET', path, token });
}

export function del(path: string, token?: string) {
	return send({ method: 'DELETE', path, token });
}

export function post(path: string, data: object, token?: string) {
	return send({ method: 'POST', path, data, token });
}

export function put(path: string, data: object, token?: string) {
	return send({ method: 'PUT', path, data, token });
}
