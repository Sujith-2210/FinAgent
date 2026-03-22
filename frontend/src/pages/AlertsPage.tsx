import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Bell, AlertTriangle, Lightbulb, Info, X, Check } from 'lucide-react'
import { authFetch, authJson } from '../lib/auth'

interface Alert {
    alert_id: string
    type: string
    severity: string
    title: string
    description: string
    triggered_by: string
    status: string
    created_at: string
}

interface AlertsData {
    alerts: Alert[]
    total: number
    unread: number
}

const severityColors: Record<string, { bg: string; text: string; border: string }> = {
    HIGH: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/50' },
    MEDIUM: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/50' },
    LOW: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/50' },
}

const typeIcons: Record<string, ReactNode> = {
    RISK: <AlertTriangle className="w-5 h-5" />,
    OPPORTUNITY: <Lightbulb className="w-5 h-5" />,
    INFO: <Info className="w-5 h-5" />,
}

export default function AlertsPage() {
    const [data, setData] = useState<AlertsData | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        let active = true
        const loadAlerts = async () => {
            try {
                const payload = await authJson<AlertsData>('/api/alerts/')
                if (!active) return
                setData(payload)
            } catch (error) {
                console.error('Failed to fetch alerts:', error)
            } finally {
                if (active) {
                    setLoading(false)
                }
            }
        }

        void loadAlerts()
        return () => {
            active = false
        }
    }, [])

    const dismissAlert = async (alertId: string) => {
        try {
            const response = await authFetch(`/api/alerts/${alertId}/dismiss`, { method: 'POST' })
            if (!response.ok) {
                throw new Error(`Failed to dismiss alert (${response.status})`)
            }
            setData(prev => prev ? {
                ...prev,
                alerts: prev.alerts.filter(a => a.alert_id !== alertId),
                unread: Math.max(prev.unread - 1, 0),
            } : null)
        } catch (error) {
            console.error('Failed to dismiss alert:', error)
        }
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full" />
            </div>
        )
    }

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">Alerts & Insights</h1>
                    <p className="text-slate-400 mt-1">Proactive financial intelligence from your AI agents</p>
                </div>
                <div className="flex items-center gap-2">
                    <Bell className="w-5 h-5 text-primary-400" />
                    <span className="badge badge-info">{data?.unread || 0} Active</span>
                </div>
            </div>

            {/* Alert Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="glass rounded-xl p-4 border-l-4 border-red-500">
                    <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="w-4 h-4 text-red-400" />
                        <span className="text-sm text-slate-400">Risk Alerts</span>
                    </div>
                    <div className="text-2xl font-bold text-red-400">
                        {data?.alerts.filter(a => a.type === 'RISK').length || 0}
                    </div>
                </div>
                <div className="glass rounded-xl p-4 border-l-4 border-green-500">
                    <div className="flex items-center gap-2 mb-2">
                        <Lightbulb className="w-4 h-4 text-green-400" />
                        <span className="text-sm text-slate-400">Opportunities</span>
                    </div>
                    <div className="text-2xl font-bold text-green-400">
                        {data?.alerts.filter(a => a.type === 'OPPORTUNITY').length || 0}
                    </div>
                </div>
                <div className="glass rounded-xl p-4 border-l-4 border-blue-500">
                    <div className="flex items-center gap-2 mb-2">
                        <Info className="w-4 h-4 text-blue-400" />
                        <span className="text-sm text-slate-400">Informational</span>
                    </div>
                    <div className="text-2xl font-bold text-blue-400">
                        {data?.alerts.filter(a => a.type === 'INFO').length || 0}
                    </div>
                </div>
            </div>

            {/* Alerts List */}
            <div className="space-y-4">
                {data?.alerts.length === 0 ? (
                    <div className="glass rounded-2xl p-8 text-center">
                        <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
                            <Check className="w-8 h-8 text-green-400" />
                        </div>
                        <h3 className="text-lg font-medium text-white mb-2">All Clear!</h3>
                        <p className="text-slate-400">No active alerts. Your finances are on track.</p>
                    </div>
                ) : (
                    data?.alerts.map((alert) => {
                        const colors = severityColors[alert.severity] || severityColors.LOW
                        return (
                            <div
                                key={alert.alert_id}
                                className={`glass rounded-xl p-4 border-l-4 ${colors.border} animate-fadeIn`}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex items-start gap-4">
                                        <div className={`w-10 h-10 rounded-xl ${colors.bg} flex items-center justify-center ${colors.text}`}>
                                            {typeIcons[alert.type] || <Info className="w-5 h-5" />}
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1">
                                                <h3 className="font-medium text-white">{alert.title}</h3>
                                                <span className={`badge ${colors.bg} ${colors.text}`}>
                                                    {alert.severity}
                                                </span>
                                            </div>
                                            <p className="text-sm text-slate-400 mb-2">{alert.description}</p>
                                            <div className="flex items-center gap-4 text-xs text-slate-500">
                                                <span>Triggered by: {alert.triggered_by}</span>
                                                <span>•</span>
                                                <span>Type: {alert.type}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => dismissAlert(alert.alert_id)}
                                        className="p-2 rounded-lg hover:bg-slate-700 transition-colors"
                                    >
                                        <X className="w-4 h-4 text-slate-400" />
                                    </button>
                                </div>
                            </div>
                        )
                    })
                )}
            </div>

            {/* How Alerts Work */}
            <div className="glass rounded-2xl p-6">
                <h2 className="text-lg font-semibold mb-4">How Alerts Work</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="glass rounded-xl p-4">
                        <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center mb-3">
                            <span className="text-lg">1</span>
                        </div>
                        <h3 className="font-medium mb-2">Signal Detection</h3>
                        <p className="text-sm text-slate-400">
                            Alert Agent monitors your financial signals for threshold breaches.
                        </p>
                    </div>
                    <div className="glass rounded-xl p-4">
                        <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center mb-3">
                            <span className="text-lg">2</span>
                        </div>
                        <h3 className="font-medium mb-2">Severity Assessment</h3>
                        <p className="text-sm text-slate-400">
                            Each alert is assigned a severity level based on impact potential.
                        </p>
                    </div>
                    <div className="glass rounded-xl p-4">
                        <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center mb-3">
                            <span className="text-lg">3</span>
                        </div>
                        <h3 className="font-medium mb-2">Action Guidance</h3>
                        <p className="text-sm text-slate-400">
                            Ask the AI Advisor for detailed recommendations on any alert.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
