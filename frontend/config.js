// ── Central API config ─────────────────────────────────────
// Change this ONE line when deploying to production:
//
//   Local:       "http://localhost:8000"
//   LAN:         "http://192.168.1.77:8000"
//   Production:  "http://108.181.168.43:8000"
//
const API = process.env.NEXT_PUBLIC_API_URL || "http://69.62.76.202:8000";

export default API;
