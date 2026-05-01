import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { Toaster } from '@/components/ui/toaster'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import Campaigns from '@/pages/Campaigns'
import Leads from '@/pages/Leads'
import Layout from '@/components/Layout'
import RoleGuard from '@/components/RoleGuard'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="campaigns" element={<Campaigns />} />
          <Route
            path="leads"
            element={
              <RoleGuard allowedRoles={['admin', 'agent']}>
                <Leads />
              </RoleGuard>
            }
          />
        </Route>
      </Routes>
      <Toaster />
    </BrowserRouter>
  )
}
