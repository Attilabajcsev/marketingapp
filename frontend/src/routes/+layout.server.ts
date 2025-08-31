export function load({ locals }) {
	return {
		user: locals.UserData,
		authed: locals.authed
	};
}
