// ── Central API config ─────────────────────────────────────
// Change this ONE line when deploying to production:
//
//   Local:       "http://localhost:8000"
//   Production:  "http://108.181.168.43:8000"
//
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default API;
