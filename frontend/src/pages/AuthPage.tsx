import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Lock, Mail, UserRound } from 'lucide-react'

import { useAuth } from '../context/AuthContext'

type AuthMode = 'login' | 'register'

interface LocationState {
    from?: {
        pathname?: string
    }
}

export default function AuthPage() {
    const [mode, setMode] = useState<AuthMode>('login')
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [fullName, setFullName] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)

    const { isAuthenticated, login, register } = useAuth()
    const navigate = useNavigate()
    const location = useLocation()

    const redirectTo = (location.state as LocationState | null)?.from?.pathname || '/'

    useEffect(() => {
        if (isAuthenticated) {
            navigate(redirectTo, { replace: true })
        }
    }, [isAuthenticated, navigate, redirectTo])

    const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        setError(null)
        setSubmitting(true)

        try {
            if (mode === 'login') {
                await login(email.trim(), password)
            } else {
                await register(fullName.trim(), email.trim(), password)
            }
        } catch (err) {
            if (err instanceof Error) {
                setError(err.message)
            } else {
                setError('Unable to authenticate')
            }
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
            <div className="w-full max-w-md glass-dark rounded-2xl p-8">
                <div className="flex items-center justify-center mb-6">
                    <img src="/assets/Logo.png" alt="FinAgent Logo" className="w-14 h-14 rounded-xl" />
                </div>

                <h1 className="text-2xl font-bold text-center gradient-text mb-2">FinAgent</h1>
                <p className="text-center text-slate-400 mb-6">
                    {mode === 'login' ? 'Sign in to your private finance workspace' : 'Create your secure account'}
                </p>

                <div className="grid grid-cols-2 gap-2 mb-6">
                    <button
                        type="button"
                        onClick={() => setMode('login')}
                        className={`py-2 rounded-lg text-sm ${mode === 'login' ? 'bg-primary-600 text-white' : 'bg-slate-800 text-slate-300'}`}
                    >
                        Sign In
                    </button>
                    <button
                        type="button"
                        onClick={() => setMode('register')}
                        className={`py-2 rounded-lg text-sm ${mode === 'register' ? 'bg-primary-600 text-white' : 'bg-slate-800 text-slate-300'}`}
                    >
                        Register
                    </button>
                </div>

                <form onSubmit={onSubmit} className="space-y-4">
                    {mode === 'register' && (
                        <label className="block">
                            <span className="text-xs text-slate-400">Full Name</span>
                            <div className="mt-1 flex items-center gap-2 bg-slate-900 rounded-lg px-3 py-2 border border-slate-700">
                                <UserRound className="w-4 h-4 text-slate-500" />
                                <input
                                    value={fullName}
                                    onChange={(e) => setFullName(e.target.value)}
                                    type="text"
                                    className="w-full bg-transparent outline-none text-sm text-slate-100"
                                    placeholder="Your name"
                                    maxLength={255}
                                    required
                                />
                            </div>
                        </label>
                    )}

                    <label className="block">
                        <span className="text-xs text-slate-400">Email</span>
                        <div className="mt-1 flex items-center gap-2 bg-slate-900 rounded-lg px-3 py-2 border border-slate-700">
                            <Mail className="w-4 h-4 text-slate-500" />
                            <input
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                type="email"
                                className="w-full bg-transparent outline-none text-sm text-slate-100"
                                placeholder="you@example.com"
                                autoComplete="email"
                                required
                            />
                        </div>
                    </label>

                    <label className="block">
                        <span className="text-xs text-slate-400">Password</span>
                        <div className="mt-1 flex items-center gap-2 bg-slate-900 rounded-lg px-3 py-2 border border-slate-700">
                            <Lock className="w-4 h-4 text-slate-500" />
                            <input
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                type="password"
                                className="w-full bg-transparent outline-none text-sm text-slate-100"
                                placeholder="At least 8 characters"
                                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                                minLength={8}
                                required
                            />
                        </div>
                    </label>

                    {error && (
                        <div className="rounded-lg border border-red-500/50 bg-red-500/10 px-3 py-2 text-sm text-red-300">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={submitting}
                        className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {submitting ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
                    </button>
                </form>

                <p className="text-xs text-center text-slate-500 mt-6">
                    By continuing, you agree to keep your credentials private.
                </p>
            </div>
        </div>
    )
}
