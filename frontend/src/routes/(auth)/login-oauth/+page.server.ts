import { redirect } from '@sveltejs/kit';
import { OAuth2Client } from 'google-auth-library';
import { env } from '$env/dynamic/private';

const GOOGLE_CLIENT_ID = env.GOOGLE_CLIENT_ID;
const GOOLGE_CLIENT_SECRET = env.GOOGLE_CLIENT_SECRET;
const redirectURL = env.GOOGLE_CLIENT_REDIRECT_URL;

export const actions = {
	OAuth2: async () => {
		const oAuth2Client = new OAuth2Client(GOOGLE_CLIENT_ID, GOOLGE_CLIENT_SECRET, redirectURL);

		const authorizeURL = oAuth2Client.generateAuthUrl({
			access_type: 'offline', // For development
			scope:
				'https://www.googleapis.com/auth/userinfo.email https://www.googleapis.com/auth/userinfo.profile openid',
			prompt: 'consent'
		});

		throw redirect(302, authorizeURL);
	}
};
