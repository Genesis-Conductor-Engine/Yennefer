export default {
  async fetch(request, env, ctx) {
    return new Response("Yennefer Conductor Active", {
      headers: { "content-type": "text/plain" },
    });
  },
};
