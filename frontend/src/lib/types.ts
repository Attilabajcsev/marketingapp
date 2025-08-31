export type ApiOptions = {
	method: string;
	headers: {
		'Content-Type'?: string;
		Authorization?: string;
	};
	body?: string;
};

export type UserState = {
	authed: boolean;
	data: UserData;
};

export type UserData = {
	id: number;
	username: string;
	email: string;
	first_name: string;
	last_name: string;
};
