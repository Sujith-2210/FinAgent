import { Outlet, NavLink } from 'react-router-dom'
import {
    MessageSquare,
    LayoutDashboard,
    Database,
    Bot,
    Bell,
    Shield,
    Settings,
    LogOut,
} from 'lucide-react'

import { useAuth } from '../context/AuthContext'

const navItems = [
    { path: '/', icon: MessageSquare, label: 'AI Advisor' },
    { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/context', icon: Database, label: 'Context' },
    { path: '/agents', icon: Bot, label: 'Agents' },
    { path: '/alerts', icon: Bell, label: 'Alerts' },
    { path: '/privacy', icon: Shield, label: 'Privacy' },
    { path: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
    const { user, logout } = useAuth()

    return (
        <div className="flex h-screen overflow-hidden">
            {/* Sidebar */}
            <aside className="w-64 glass-dark flex flex-col">
                {/* Logo */}
                <div className="p-6 border-b border-slate-700/50">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl flex items-center justify-center overflow-hidden">
                            <img src="/assets/Logo.png" alt="FinAgent Logo" className="w-full h-full object-cover" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold gradient-text">FinAgent</h1>
                            <p className="text-xs text-slate-400">AI Financial Advisor</p>
                        </div>
                    </div>
                </div>

                {/* Navigation */}
                <nav className="flex-1 p-4 space-y-2">
                    {navItems.map((item) => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            className={({ isActive }) =>
                                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${isActive
                                    ? 'gradient-accent text-white shadow-lg'
                                    : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                                }`
                            }
                        >
                            <item.icon className="w-5 h-5" />
                            <span className="font-medium">{item.label}</span>
                        </NavLink>
                    ))}
                </nav>

                {/* Status */}
                <div className="p-4 border-t border-slate-700/50">
                    <div className="glass rounded-xl p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                            <span className="text-sm text-slate-300">System Active</span>
                        </div>
                        {user?.email && (
                            <p className="text-xs text-slate-500 truncate mb-2">
                                Signed in as <span className="text-slate-300">{user.email}</span>
                            </p>
                        )}
                        <p className="text-xs text-slate-500">
                            Privacy Level: <span className="text-primary-400">HIGH</span>
                        </p>
                        <button
                            onClick={logout}
                            className="mt-3 w-full text-xs px-3 py-2 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 flex items-center justify-center gap-2"
                        >
                            <LogOut className="w-3 h-3" />
                            Sign Out
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 overflow-auto">
                <div className="p-8">
                    <Outlet />
                </div>
            </main>
        </div>
    )
}
