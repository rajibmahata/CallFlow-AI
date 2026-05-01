import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { authApi } from '@/api/client'

export function useAuth() {
  const { token, user, setUser, logout } = useAuthStore()
  const navigate = useNavigate()

  useEffect(() => {
    if (token && !user) {
      authApi.me()
        .then((res) => setUser(res.data as Parameters<typeof setUser>[0]))
        .catch(() => logout())
    }
  }, [token, user, setUser, logout])

  return { token, user, logout: () => { logout(); navigate('/login') } }
}
