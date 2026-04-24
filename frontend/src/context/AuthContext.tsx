/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import {
    authJson,
    clearAuthSession,
    getStoredToken,
    getStoredUser,
    storeAuthSession,
    type AuthTokenResponse,
    type AuthUser,
} from '../lib/auth'

interface AuthContextValue {
    user: AuthUser | null
    token: string | null
    loading: boolean
    isAuthenticated: boolean
    login: (email: string, password: string) => Promise<void>
    register: (fullName: string, email: string, password: string) => Promise<void>
    logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

const parseErrorMessage = async (response: Response): Promise<string> => {
    const fallback = `Authentication failed (${response.status})`
    const raw = await response.text()
    if (!raw) return fallback

    try {
        const parsed = JSON.parse(raw) as { detail?: string }
        if (parsed && typeof parsed.detail === 'string' && parsed.detail.trim()) {
            return parsed.detail
        }
        return raw
    } catch {
        return raw
    }
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [token, setToken] = useState<string | null>(() => getStoredToken())
    const [user, setUser] = useState<AuthUser | null>(() => getStoredUser())
    const [loading, setLoading] = useState<boolean>(Boolean(getStoredToken()))

    useEffect(() => {
        let active = true
        const validateSession = async () => {
            if (!token) {
                if (active) {
                    setLoading(false)
                    setUser(null)
                }
                return
            }

            setLoading(true)
            try {
                const currentUser = await authJson<AuthUser>('/api/auth/me')
                if (!active) return
                setUser(currentUser)
            } catch {
                if (!active) return
                clearAuthSession()
                setToken(null)
                setUser(null)
            } finally {
                if (active) {
                    setLoading(false)
                }
            }
        }

        void validateSession()
        return () => {
            active = false
        }
    }, [token])

    const handleAuthResponse = async (response: Response) => {
        if (!response.ok) {
            throw new Error(await parseErrorMessage(response))
        }

        const data = await response.json() as AuthTokenResponse
        storeAuthSession(data)
        setToken(data.access_token)
        setUser(data.user)
    }

    const login = async (email: string, password: string) => {
        const params = new URLSearchParams()
        params.append('username', email)
        params.append('password', password)

        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params,
        })
        await handleAuthResponse(response)
    }

    const register = async (fullName: string, email: string, password: string) => {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email,
                password,
                full_name: fullName.trim() || null,
            }),
        })
        await handleAuthResponse(response)
    }

    const logout = () => {
        clearAuthSession()
        setToken(null)
        setUser(null)
    }

    const value: AuthContextValue = {
        user,
        token,
        loading,
        isAuthenticated: Boolean(token && user),
        login,
        register,
        logout,
    }

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = (): AuthContextValue => {
    const context = useContext(AuthContext)
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider')
    }
    return context
}
