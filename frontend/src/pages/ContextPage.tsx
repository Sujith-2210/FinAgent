import { useEffect, useState } from 'react'
import { Database, RefreshCw, Clock, Layers, Lock, Wallet, CreditCard, ArrowUpDown } from 'lucide-react'
import { authFetch, authJson } from '../lib/auth'

interface ContextData {
    context_id: string
    context_version: number
    privacy_level: string
    layers: Record<string, Record<string, unknown>>
}

interface FiMoneyData {
    source: string
    user_id: string
    last_sync: string | null
    net_worth: {
        band: string
        asset_classes: string[]
        liabilities: string[]
        debt_intensity: string
    }
    credit_report: {
        score_band: string
        utilization_band: string
        active_loans: number
    }
    insights: {
        income_band: string
        savings_rate_band: string
        expense_band: string
        top_expense_categories: string[]
    }
}

const layerColors: Record<string, string> = {
    user_financial_context: 'border-blue-500/50',
    transactional_signals: 'border-green-500/50',
    user_goals_context: 'border-purple-500/50',
    external_knowledge_context: 'border-orange-500/50',
    agent_working_memory: 'border-yellow-500/50',
    explainability_context: 'border-pink-500/50',
    alert_context: 'border-red-500/50',
}

export default function ContextPage() {
    const [context, setContext] = useState<ContextData | null>(null)
    const [fiMoneyData, setFiMoneyData] = useState<FiMoneyData | null>(null)
    const [loading, setLoading] = useState(true)
    const [syncing, setSyncing] = useState(false)

    const fetchContext = async () => {
        try {
            const data = await authJson<ContextData>('/api/context/')
            setContext(data)
        } catch (error) {
            console.error('Failed to fetch context:', error)
        } finally {
            setLoading(false)
        }
    }

    const fetchFiMoneyData = async () => {
        try {
            const data = await authJson<FiMoneyData>('/api/context/fi-money')
            setFiMoneyData(data)
        } catch (error) {
            console.error('Failed to fetch Fi-Money data:', error)
        }
    }

    const syncContext = async () => {
        setSyncing(true)
        try {
            const response = await authFetch('/api/context/sync', { method: 'POST' })
            if (!response.ok) {
                throw new Error(`Sync failed (${response.status})`)
            }
            await fetchContext()
            await fetchFiMoneyData()
        } catch (error) {
            console.error('Sync failed:', error)
        } finally {
            setSyncing(false)
        }
    }

    useEffect(() => {
        void fetchContext()
        void fetchFiMoneyData()
    }, [])

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
                    <h1 className="text-3xl font-bold gradient-text">MCP Context Viewer</h1>
                    <p className="text-slate-400 mt-1">View and manage your financial context layers</p>
                </div>
                <button
                    onClick={syncContext}
                    disabled={syncing}
                    className="btn-primary flex items-center gap-2"
                >
                    <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
                    Sync Context
                </button>
            </div>

            {/* Context Info */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="glass rounded-xl p-4">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                        <Database className="w-4 h-4" />
                        <span className="text-sm">Context ID</span>
                    </div>
                    <p className="text-sm font-mono text-primary-400 truncate">
                        {context?.context_id || 'N/A'}
                    </p>
                </div>
                <div className="glass rounded-xl p-4">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                        <Clock className="w-4 h-4" />
                        <span className="text-sm">Version</span>
                    </div>
                    <p className="text-2xl font-bold">{context?.context_version || 0}</p>
                </div>
                <div className="glass rounded-xl p-4">
                    <div className="flex items-center gap-2 text-slate-400 mb-2">
                        <Lock className="w-4 h-4" />
                        <span className="text-sm">Privacy Level</span>
                    </div>
                    <span className="badge badge-success">{context?.privacy_level || 'HIGH'}</span>
                </div>
            </div>

            {/* Fi-Money MCP Data Section */}
            {fiMoneyData && (
                <div className="space-y-4">
                    <h2 className="text-lg font-semibold flex items-center gap-2">
                        <Wallet className="w-5 h-5 text-emerald-400" />
                        Fi-Money MCP Data
                        <span className="text-xs text-slate-500 ml-2">Source: {fiMoneyData.source}</span>
                    </h2>

                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {/* Net Worth */}
                        <div className="glass rounded-xl p-4 border-l-4 border-emerald-500/50">
                            <h3 className="font-medium mb-3 flex items-center gap-2">
                                <Wallet className="w-4 h-4 text-emerald-400" />
                                Net Worth Band: {fiMoneyData.net_worth.band}
                            </h3>
                            <div className="space-y-2">
                                <div className="text-sm text-slate-400">Asset Classes</div>
                                <div className="flex flex-wrap gap-2">
                                    {(fiMoneyData.net_worth.asset_classes.length > 0 ? fiMoneyData.net_worth.asset_classes : ['None']).map((assetClass, i) => (
                                        <span key={i} className="badge badge-success text-xs">
                                            {assetClass}
                                        </span>
                                    ))}
                                </div>
                                <div className="text-sm text-slate-400 mt-3">Liabilities</div>
                                <div className="flex flex-wrap gap-2">
                                    {(fiMoneyData.net_worth.liabilities.length > 0 ? fiMoneyData.net_worth.liabilities : ['None']).map((liabilityType, i) => (
                                        <span key={i} className="badge badge-warning text-xs">
                                            {liabilityType}
                                        </span>
                                    ))}
                                </div>
                                <div className="flex justify-between text-sm mt-3">
                                    <span className="text-slate-400">Debt Intensity</span>
                                    <span className="text-slate-300">{fiMoneyData.net_worth.debt_intensity}</span>
                                </div>
                            </div>
                        </div>

                        {/* Credit Report */}
                        <div className="glass rounded-xl p-4 border-l-4 border-blue-500/50">
                            <h3 className="font-medium mb-3 flex items-center gap-2">
                                <CreditCard className="w-4 h-4 text-blue-400" />
                                Credit Report
                            </h3>
                            <div className="space-y-2">
                                <div className="flex justify-between items-center">
                                    <span className="text-slate-400 text-sm">Score Band</span>
                                    <span className="text-2xl font-bold text-blue-400">{fiMoneyData.credit_report.score_band}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-400">Utilization</span>
                                    <span className="badge badge-info">{fiMoneyData.credit_report.utilization_band}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-400">Active Loans</span>
                                    <span className="text-slate-300">{fiMoneyData.credit_report.active_loans}</span>
                                </div>
                            </div>
                        </div>

                        {/* Derived Insights */}
                        <div className="glass rounded-xl p-4 border-l-4 border-purple-500/50">
                            <h3 className="font-medium mb-3 flex items-center gap-2">
                                <ArrowUpDown className="w-4 h-4 text-purple-400" />
                                Derived Insights
                            </h3>
                            <div className="space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-400">Income Band</span>
                                    <span className="text-slate-300">{fiMoneyData.insights.income_band}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-400">Expense Band</span>
                                    <span className="text-slate-300">{fiMoneyData.insights.expense_band}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-slate-400">Savings Rate</span>
                                    <span className="text-slate-300">{fiMoneyData.insights.savings_rate_band}</span>
                                </div>
                                <div className="text-sm text-slate-400 mt-2">Top Expense Categories</div>
                                <div className="flex flex-wrap gap-2">
                                    {(fiMoneyData.insights.top_expense_categories.length > 0
                                        ? fiMoneyData.insights.top_expense_categories
                                        : ['Uncategorized']).map((category, i) => (
                                            <span key={i} className="badge badge-info text-xs">
                                                {category}
                                            </span>
                                        ))}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Context Layers */}
            <div className="space-y-4">
                <h2 className="text-lg font-semibold flex items-center gap-2">
                    <Layers className="w-5 h-5 text-primary-400" />
                    Context Layers (7 Layers)
                </h2>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {context?.layers && Object.entries(context.layers).map(([layerName, layerData]) => (
                        <div
                            key={layerName}
                            className={`glass rounded-xl p-4 border-l-4 ${layerColors[layerName] || 'border-slate-500/50'}`}
                        >
                            <div className="flex items-center justify-between mb-3">
                                <h3 className="font-medium capitalize">
                                    {layerName.replace(/_/g, ' ')}
                                </h3>
                                <span className="text-xs text-slate-500">
                                    {String(layerData.source ?? 'system')}
                                </span>
                            </div>

                            <div className="space-y-2">
                                {typeof layerData.data === 'object' && layerData.data !== null && Object.entries(layerData.data as Record<string, unknown>).map(([key, value]) => (
                                    <div key={key} className="flex items-center justify-between text-sm">
                                        <span className="text-slate-400 capitalize">{key.replace(/_/g, ' ')}</span>
                                        <span className="text-slate-300">
                                            {typeof value === 'object'
                                                ? JSON.stringify(value).slice(0, 30) + '...'
                                                : String(value) || 'N/A'
                                            }
                                        </span>
                                    </div>
                                ))}

                                {typeof layerData.signals === 'object' && layerData.signals !== null && Object.entries(layerData.signals as Record<string, unknown>).map(([key, value]) => (
                                    <div key={key} className="flex items-center justify-between text-sm">
                                        <span className="text-slate-400 capitalize">{key.replace(/_/g, ' ')}</span>
                                        <span className={`badge ${value === 'HIGH' ? 'badge-danger' :
                                            value === 'MEDIUM' ? 'badge-warning' : 'badge-success'
                                            }`}>
                                            {String(value) || 'N/A'}
                                        </span>
                                    </div>
                                ))}

                                {Array.isArray(layerData.goals) && (
                                    <div className="text-sm text-slate-400">
                                        {layerData.goals.length} goals defined
                                    </div>
                                )}

                                {Array.isArray(layerData.knowledge_items) && (
                                    <div className="text-sm text-slate-400">
                                        {layerData.knowledge_items.length} knowledge items
                                    </div>
                                )}

                                {Array.isArray(layerData.entries) && (
                                    <div className="text-sm text-slate-400">
                                        {layerData.entries.length} entries
                                    </div>
                                )}

                                {Array.isArray(layerData.agent_trace) && (
                                    <div className="text-sm text-slate-400">
                                        {layerData.agent_trace.length} agent traces
                                    </div>
                                )}

                                {Array.isArray(layerData.active_alerts) && (
                                    <div className="text-sm text-slate-400">
                                        {layerData.active_alerts.length} active alerts
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Layer Legend */}
            <div className="glass rounded-xl p-4">
                <h3 className="text-sm font-medium text-slate-300 mb-3">Layer Types</h3>
                <div className="flex flex-wrap gap-3">
                    {Object.entries(layerColors).map(([layer, color]) => (
                        <div key={layer} className="flex items-center gap-2">
                            <div className={`w-3 h-3 rounded border-2 ${color}`} />
                            <span className="text-xs text-slate-400 capitalize">
                                {layer.replace(/_/g, ' ')}
                            </span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}
