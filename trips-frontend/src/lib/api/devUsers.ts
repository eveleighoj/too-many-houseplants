/** clerk-mock's dev users, each with a ready-made token (local development only; see
 * mocks/clerk/README.md). */
export type DevUser = { id: string; name: string; email: string; token: string };

export async function fetchDevUsers(mockAuthUrl: string): Promise<DevUser[]> {
	const response = await fetch(`${mockAuthUrl}/dev/users`);
	if (!response.ok) throw new Error(`clerk-mock returned ${response.status}`);
	return (await response.json()).users;
}
