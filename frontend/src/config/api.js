// API Configuration
// Default: same-origin (works with nginx /api proxy + Vite dev proxy)
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export { API_BASE_URL }
