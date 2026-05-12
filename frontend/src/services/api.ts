import axios from 'axios'

const API_BASE_URL = 'http://localhost:8000/api/v1'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// REQUEST INTERCEPTOR
api.interceptors.request.use((config) => {
  const authStorage = localStorage.getItem('bioattend-auth')

  if (authStorage) {
    try {
      const parsed = JSON.parse(authStorage)

      const token = parsed?.state?.token

      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    } catch (err) {
      console.error('Token parse error', err)
    }
  }

  return config
})

// AUTH APIs
export const authApi = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', {
      email,
      password,
    })

    return response.data
  },

  me: async () => {
    const response = await api.get('/auth/me')

    return response.data
  },
}

export default api