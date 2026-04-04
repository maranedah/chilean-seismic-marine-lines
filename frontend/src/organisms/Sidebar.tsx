'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { clsx } from 'clsx'

const NAV_ITEMS = [
  { href: '/map', label: 'Maps', icon: '🗺️' },
  { href: '/database', label: 'Database', icon: '📋' },
  { href: '/reports', label: 'Reports', icon: '📊' },
]

export default function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-56 bg-slate-900 text-white flex flex-col shrink-0 border-r border-slate-800">
      {/* Brand */}
      <div className="px-5 py-5 border-b border-slate-800">
        <div className="text-2xl mb-1.5">🌊</div>
        <h1 className="font-bold text-white text-sm leading-tight">Chilean Marine</h1>
        <p className="text-slate-400 text-xs mt-0.5">Seismic Lines Database</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                isActive
                  ? 'bg-ocean-600 text-white shadow-sm'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white',
              )}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-slate-800">
        <p className="text-xs text-slate-500">~98 surveys</p>
        <p className="text-xs text-slate-600 mt-0.5">1987 – 2025</p>
      </div>
    </aside>
  )
}
