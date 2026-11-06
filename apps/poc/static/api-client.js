/* Transport only. Inject fetch for alternate hosts and isolated component tests. */
const BattleApi = {
  create({fetch: transport, baseUrl = ''}) {
    async function request(path, options) {
      const response = await transport(baseUrl + path, options);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Request failed');
      return data;
    }
    return Object.freeze({
      get: path => request(path),
      post: (path, body) => request(path, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body),
      }),
    });
  },
};
