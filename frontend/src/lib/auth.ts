export interface AuthUser {
    user_id: string
    email: string
    full_name?: string | null
    is_active: boolean
    created_at: string
}

export interface AuthTokenResponse {
    access_token: string
    token_type: string
    expires_in_minutes: number
    user: AuthUser
}

const AUTH_TOKEN_KEY = 'finagent_auth_token'
const AUTH_USER_KEY = 'finagent_auth_user'

const isBrowser = typeof window !== 'undefined'

export const getStoredToken = (): string | null => {
    if (!isBrowser) return null
    return localStorage.getItem(AUTH_TOKEN_KEY)
}

export const getStoredUser = (): AuthUser | null => {
    if (!isBrowser) return null
    const raw = localStorage.getItem(AUTH_USER_KEY)
    if (!raw) return null
    try {
        return JSON.parse(raw) as AuthUser
    } catch {
        return null
    }
}

export const storeAuthSession = (payload: AuthTokenResponse): void => {
    if (!isBrowser) return
    localStorage.setItem(AUTH_TOKEN_KEY, payload.access_token)
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(payload.user))
}

export const clearAuthSession = (): void => {
    if (!isBrowser) return
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(AUTH_USER_KEY)
    localStorage.removeItem('finagent_session_id')
}

const extractErrorMessage = async (response: Response): Promise<string> => {
    const fallback = `Request failed (${response.status})`
    const bodyText = await response.text()
    if (!bodyText) return fallback

    try {
        const parsed = JSON.parse(bodyText) as { detail?: string }
        if (parsed && typeof parsed.detail === 'string' && parsed.detail.trim()) {
            return parsed.detail
        }
        return bodyText
    } catch {
        return bodyText
    }
}

export const authFetch = async (input: string, init: RequestInit = {}): Promise<Response> => {
    const token = getStoredToken()
    const headers = new Headers(init.headers ?? {})

    if (token && !headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${token}`)
    }

    const response = await fetch(input, {
        ...init,
        headers,
    })

    if (response.status === 401 && token) {
        clearAuthSession()
        if (isBrowser && window.location.pathname !== '/auth') {
            window.location.assign('/auth')
        }
    }

    return response
}

export const authJson = async <T>(input: string, init: RequestInit = {}): Promise<T> => {
    const response = await authFetch(input, init)
    if (!response.ok) {
        throw new Error(await extractErrorMessage(response))
    }
    return response.json() as Promise<T>
}
