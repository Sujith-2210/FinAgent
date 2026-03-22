import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'

import { useAuth } from '../context/AuthContext'

export default function RequireAuth({ children }: { children: ReactNode }) {
    const { isAuthenticated, loading } = useAuth()
    const location = useLocation()

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full" />
            </div>
        )
    }

    if (!isAuthenticated) {
        return <Navigate to="/auth" replace state={{ from: location }} />
    }

    return <>{children}</>
}
