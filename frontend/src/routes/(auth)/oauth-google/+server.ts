import { redirect } from '@sveltejs/kit';
import { OAuth2Client } from 'google-auth-library';
import { env } from '$env/dynamic/private';
import * as api from '$lib/api.js';

const GOOGLE_CLIENT_ID = env.GOOGLE_CLIENT_ID;
const GOOLGE_CLIENT_SECRET = env.GOOGLE_CLIENT_SECRET;
const redirectURL = env.GOOGLE_CLIENT_REDIRECT_URL;

export const GET = async (event) => {
	const code = await event.url.searchParams.get('code');

	try {
		const oAuth2Client = new OAuth2Client(GOOGLE_CLIENT_ID, GOOLGE_CLIENT_SECRET, redirectURL);

		const responseGoogle = await oAuth2Client.getToken(code);
		oAuth2Client.setCredentials(responseGoogle.tokens);
		console.log(`Auth tokens recieved`);

		const data: { access: string; refresh: string } = await api.post('oauth-google/', {
			id_token: oAuth2Client.credentials['id_token']
		});
		const accessToken = data.access;
		const refreshToken = data.refresh;

		event.cookies.set('accessToken', accessToken, {
			httpOnly: true,
			path: '/',
			maxAge: 60 * 60,
			sameSite: 'lax'
		}); //expires in 1h

		event.cookies.set('refreshToken', refreshToken, {
			httpOnly: true,
			path: '/',
			maxAge: 60 * 60 * 24 * 7,
			sameSite: 'lax'
		}); // expires in 1 week
	} catch (err) {
		console.log(`Error with Google Auth ${err}`);
	}
	throw redirect(303, '/');
};
