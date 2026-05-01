import { useAuthStore } from '@/stores/authStore'
import { Navigate } from 'react-router-dom'

interface RoleGuardProps {
  allowedRoles: string[]
  children: React.ReactNode
}

export default function RoleGuard({ allowedRoles, children }: RoleGuardProps) {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  if (!allowedRoles.includes(user.role)) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <h2 className="text-xl font-semibold">Access Denied</h2>
          <p className="text-muted-foreground mt-1">You don't have permission to view this page.</p>
        </div>
      </div>
    )
  }
  return <>{children}</>
}
