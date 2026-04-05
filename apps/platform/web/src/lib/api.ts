import axios from "axios"

export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login"
    }
    return Promise.reject(err)
  }
)

// Auth
export const login = (username: string, password: string) =>
  api.post("/auth/login", { username, password })

export const logout = () => api.post("/auth/logout")

export const getSession = () => api.get("/auth/session")

// Data
export const getDashboard = () => api.get("/dashboard")
export const getAccounts = () => api.get("/accounts")
export const getEnvelopes = (period?: string) =>
  api.get("/envelopes", { params: period ? { period } : {} })

export const patchEnvelopeAssign = (id: number, period: string, assigned: number) =>
  api.patch(`/envelopes/${id}/assign`, { assigned }, { params: { period } })

export const getScheduled = () => api.get("/scheduled")
export const getTransactions = (params?: {
  period?: string
  account_id?: number
  envelope_id?: number
  search?: string
  limit?: number
  offset?: number
}) => api.get("/transactions", { params })

export const postTransaction = (body: {
  amount: number
  type: string
  account_id: number
  payee?: string
  memo?: string
  envelope_id?: number
  to_account_id?: number
  date?: string
}) => api.post("/transactions", body)
