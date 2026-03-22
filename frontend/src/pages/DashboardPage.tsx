import { useEffect, useState } from 'react'
import {
    TrendingUp,
    TrendingDown,
    Wallet,
    CreditCard,
    PiggyBank,
    ArrowUpRight,
    ArrowDownRight,
    Activity,
    Download,
    Printer,
    Languages,
    GripVertical,
    Save,
    RotateCcw
} from 'lucide-react'
import { useI18n } from '../context/I18nContext'
import { authJson } from '../lib/auth'

interface DashboardData {
    net_worth: {
        band: string
        trend: string
        asset_breakdown: Record<string, string>
        liability_breakdown: Record<string, string>
    }
    credit_health: {
        score_band: string
        utilization_band: string
        active_loans: number
        on_time_payments: string
    }
    cash_flow: {
        income_band: string
        expense_band: string
        savings_rate_band: string
        top_expense_categories: string[]
    }
}

const getBandColor = (band: string) => {
    switch (band?.toUpperCase()) {
        case 'HIGH':
        case 'EXCELLENT':
        case 'GOOD':
            return 'text-green-400'
        case 'MEDIUM':
        case 'FAIR':
            return 'text-yellow-400'
        case 'LOW':
        case 'POOR':
            return 'text-red-400'
        default:
            return 'text-slate-400'
    }
}

const getBandBg = (band: string) => {
    switch (band?.toUpperCase()) {
        case 'HIGH':
        case 'EXCELLENT':
        case 'GOOD':
            return 'bg-green-500/20'
        case 'MEDIUM':
        case 'FAIR':
            return 'bg-yellow-500/20'
        case 'LOW':
        case 'POOR':
            return 'bg-red-500/20'
        default:
            return 'bg-slate-500/20'
    }
}

export default function DashboardPage() {
    const [data, setData] = useState<DashboardData | null>(null)
    const [loading, setLoading] = useState(true)
    const { t, language, setLanguage } = useI18n()

    // Customization State
    const [isEditing, setIsEditing] = useState(false)
    const [widgetOrder, setWidgetOrder] = useState<string[]>(() => {
        const savedOrder = localStorage.getItem('dashboard_widget_order')
        if (!savedOrder) {
            return ['net_worth', 'credit_health', 'savings_rate', 'credit_utilization']
        }
        try {
            const parsed = JSON.parse(savedOrder)
            if (Array.isArray(parsed) && parsed.every((item) => typeof item === 'string')) {
                return parsed
            }
        } catch {
            // Fall through to default order.
        }
        return ['net_worth', 'credit_health', 'savings_rate', 'credit_utilization']
    })
    const [draggedItem, setDraggedItem] = useState<string | null>(null)

    const handleSaveLayout = () => {
        localStorage.setItem('dashboard_widget_order', JSON.stringify(widgetOrder))
        setIsEditing(false)
    }

    const handleResetLayout = () => {
        setWidgetOrder(['net_worth', 'credit_health', 'savings_rate', 'credit_utilization'])
        localStorage.removeItem('dashboard_widget_order')
        setIsEditing(false)
    }

    // Drag Handlers
    const handleDragStart = (e: React.DragEvent, id: string) => {
        setDraggedItem(id)
        e.dataTransfer.effectAllowed = 'move'
        // Ghost image usually handled by browser, but we can customize if needed
    }

    const handleDragOver = (e: React.DragEvent, id: string) => {
        e.preventDefault()
        if (draggedItem === id) return

        // Simple swap logic
        const oldIndex = widgetOrder.indexOf(draggedItem!)
        const newIndex = widgetOrder.indexOf(id)

        if (oldIndex !== -1 && newIndex !== -1) {
            const newOrder = [...widgetOrder]
            newOrder.splice(oldIndex, 1)
            newOrder.splice(newIndex, 0, draggedItem!)
            setWidgetOrder(newOrder)
        }
    }

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault()
        setDraggedItem(null)
    }

    useEffect(() => {
        let active = true
        const loadDashboard = async () => {
            try {
                const payload = await authJson<DashboardData>('/api/dashboard/')
                if (!active) return
                setData(payload)
            } catch (error) {
                console.error('Failed to fetch dashboard:', error)
            } finally {
                if (active) {
                    setLoading(false)
                }
            }
        }

        void loadDashboard()
        return () => {
            active = false
        }
    }, [])

    const handleExportCSV = () => {
        if (!data) return;

        const csvRows = [
            ['Metric', 'Value', 'Band'],
            ['Net Worth', '', data.net_worth.band],
            ['Credit Score', data.credit_health.on_time_payments, data.credit_health.score_band],
            ['Savings Rate', '', data.cash_flow.savings_rate_band],
            ['Income', '', data.cash_flow.income_band],
            ['Expenses', '', data.cash_flow.expense_band]
        ];

        const csvContent = "data:text/csv;charset=utf-8,"
            + csvRows.map(e => e.join(",")).join("\n");

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `finagent_report_${new Date().toISOString().split('T')[0]}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const handlePrint = () => {
        window.print();
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full" />
            </div>
        )
    }

    return (
        <div className="space-y-8 print:space-y-4">
            <div className="flex justify-between items-start">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">{t('dashboard.title')}</h1>
                    <p className="text-slate-400 mt-1">{t('dashboard.subtitle')}</p>
                </div>
                <div className="flex gap-2 print:hidden">
                    {isEditing ? (
                        <>
                            <button onClick={handleResetLayout} className="btn btn-ghost flex items-center gap-2 text-slate-400 hover:text-white">
                                <RotateCcw className="w-4 h-4" />
                                <span className="hidden sm:inline">Reset</span>
                            </button>
                            <button onClick={handleSaveLayout} className="btn btn-primary flex items-center gap-2">
                                <Save className="w-4 h-4" />
                                Save Layout
                            </button>
                        </>
                    ) : (
                        <button onClick={() => setIsEditing(true)} className="btn btn-outline flex items-center gap-2">
                            <GripVertical className="w-4 h-4" />
                            <span className="hidden sm:inline">Customize</span>
                        </button>
                    )}

                    <button
                        onClick={() => setLanguage(language === 'en' ? 'hi' : 'en')}
                        className="btn btn-ghost flex items-center gap-2"
                        title="Switch Language"
                    >
                        <Languages className="w-5 h-5" />
                        <span className="uppercase">{language}</span>
                    </button>
                    <button onClick={handleExportCSV} className="btn btn-outline flex items-center gap-2">
                        <Download className="w-4 h-4" />
                        {t('action.export_csv')}
                    </button>
                    <button onClick={handlePrint} className="btn btn-primary flex items-center gap-2">
                        <Printer className="w-4 h-4" />
                        {t('action.print')}
                    </button>
                </div>
            </div>

            {/* Main Metrics - Draggable Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {widgetOrder.map((widgetId) => {
                    const isDragging = draggedItem === widgetId;

                    // Render correct widget based on ID
                    let content = null;
                    if (widgetId === 'net_worth') {
                        content = (
                            <>
                                <div className="flex items-center justify-between mb-4">
                                    <div className="w-12 h-12 rounded-xl bg-primary-500/20 flex items-center justify-center">
                                        <Wallet className="w-6 h-6 text-primary-400" />
                                    </div>
                                    {data?.net_worth.trend === 'up' ? (
                                        <ArrowUpRight className="w-5 h-5 text-green-400" />
                                    ) : (
                                        <ArrowDownRight className="w-5 h-5 text-red-400" />
                                    )}
                                </div>
                                <h3 className="text-sm text-slate-400 mb-1">{t('metric.net_worth')}</h3>
                                <div className={`text-2xl font-bold ${getBandColor(data?.net_worth.band || '')}`}>
                                    {data?.net_worth.band}
                                </div>
                                <p className="text-xs text-slate-500 mt-2">Privacy-masked value</p>
                            </>
                        );
                    } else if (widgetId === 'credit_health') {
                        content = (
                            <>
                                <div className="flex items-center justify-between mb-4">
                                    <div className="w-12 h-12 rounded-xl bg-accent-500/20 flex items-center justify-center">
                                        <CreditCard className="w-6 h-6 text-accent-400" />
                                    </div>
                                    <span className={`badge ${getBandBg(data?.credit_health.score_band || '')} ${getBandColor(data?.credit_health.score_band || '')}`}>
                                        {data?.credit_health.score_band}
                                    </span>
                                </div>
                                <h3 className="text-sm text-slate-400 mb-1">{t('metric.credit_score')}</h3>
                                <div className="text-2xl font-bold text-white">
                                    {data?.credit_health.on_time_payments}
                                </div>
                                <p className="text-xs text-slate-500 mt-2">On-time payments</p>
                            </>
                        );
                    } else if (widgetId === 'savings_rate') {
                        content = (
                            <>
                                <div className="flex items-center justify-between mb-4">
                                    <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center">
                                        <PiggyBank className="w-6 h-6 text-green-400" />
                                    </div>
                                    <Activity className="w-5 h-5 text-slate-400" />
                                </div>
                                <h3 className="text-sm text-slate-400 mb-1">{t('metric.savings_rate')}</h3>
                                <div className={`text-2xl font-bold ${getBandColor(data?.cash_flow.savings_rate_band || '')}`}>
                                    {data?.cash_flow.savings_rate_band}
                                </div>
                                <p className="text-xs text-slate-500 mt-2">Monthly savings</p>
                            </>
                        );
                    } else if (widgetId === 'credit_utilization') {
                        content = (
                            <>
                                <div className="flex items-center justify-between mb-4">
                                    <div className="w-12 h-12 rounded-xl bg-yellow-500/20 flex items-center justify-center">
                                        <TrendingUp className="w-6 h-6 text-yellow-400" />
                                    </div>
                                </div>
                                <h3 className="text-sm text-slate-400 mb-1">{t('metric.utilization')}</h3>
                                <div className={`text-2xl font-bold ${getBandColor(data?.credit_health.utilization_band || '')}`}>
                                    {data?.credit_health.utilization_band}
                                </div>
                                <p className="text-xs text-slate-500 mt-2">{data?.credit_health.active_loans} active loans</p>
                            </>
                        );
                    }

                    return (
                        <div
                            key={widgetId}
                            draggable={isEditing}
                            onDragStart={(e) => handleDragStart(e, widgetId)}
                            onDragOver={(e) => handleDragOver(e, widgetId)}
                            onDrop={handleDrop}
                            className={`metric-card transition-all ${isEditing ? 'cursor-move ring-2 ring-primary-500/50 hover:bg-slate-800' : ''
                                } ${isDragging ? 'opacity-50 scale-95' : ''}`}
                        >
                            {isEditing && (
                                <div className="absolute top-2 right-2 text-slate-600">
                                    <GripVertical className="w-4 h-4" />
                                </div>
                            )}
                            {content}
                        </div>
                    )
                })}
            </div>

            {/* Asset & Liability Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Assets */}
                <div className="glass rounded-2xl p-6">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-green-400" />
                        {t('section.assets')}
                    </h2>
                    <div className="space-y-3">
                        {Object.entries(data?.net_worth.asset_breakdown || {}).map(([key, value]) => (
                            <div key={key} className="flex items-center justify-between p-3 glass rounded-xl">
                                <span className="text-slate-300 capitalize">{key.replace(/_/g, ' ')}</span>
                                <span className={`badge ${value === 'present' ? 'badge-success' : 'badge-warning'}`}>
                                    {value}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Liabilities */}
                <div className="glass rounded-2xl p-6">
                    <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <TrendingDown className="w-5 h-5 text-red-400" />
                        {t('section.liabilities')}
                    </h2>
                    <div className="space-y-3">
                        {Object.entries(data?.net_worth.liability_breakdown || {}).map(([key, value]) => (
                            <div key={key} className="flex items-center justify-between p-3 glass rounded-xl">
                                <span className="text-slate-300 capitalize">{key.replace(/_/g, ' ')}</span>
                                <span className={`badge ${value === 'none' ? 'badge-success' : 'badge-warning'}`}>
                                    {value}
                                </span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Cash Flow */}
            <div className="glass rounded-2xl p-6 print:break-inside-avoid">
                <h2 className="text-lg font-semibold mb-4">{t('section.cash_flow')}</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="glass rounded-xl p-4 text-center">
                        <p className="text-sm text-slate-400 mb-2">{t('label.income_band')}</p>
                        <p className={`text-xl font-bold ${getBandColor(data?.cash_flow.income_band || '')}`}>
                            {data?.cash_flow.income_band}
                        </p>
                    </div>
                    <div className="glass rounded-xl p-4 text-center">
                        <p className="text-sm text-slate-400 mb-2">{t('label.expense_band')}</p>
                        <p className={`text-xl font-bold ${getBandColor(data?.cash_flow.expense_band || '')}`}>
                            {data?.cash_flow.expense_band}
                        </p>
                    </div>
                    <div className="glass rounded-xl p-4 text-center">
                        <p className="text-sm text-slate-400 mb-2">{t('label.top_expenses')}</p>
                        <div className="flex flex-wrap gap-1 justify-center">
                            {data?.cash_flow.top_expense_categories.map(cat => (
                                <span key={cat} className="badge badge-info capitalize">{cat}</span>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Privacy Notice */}
            <div className="glass rounded-2xl p-6 border border-green-500/20">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                        <span className="text-green-400">🔒</span>
                    </div>
                    <div>
                        <h3 className="font-medium text-green-400">{t('privacy.title')}</h3>
                        <p className="text-sm text-slate-400">
                            {t('privacy.desc')}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
