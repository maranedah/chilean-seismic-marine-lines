import type { Metadata } from 'next'
import 'leaflet/dist/leaflet.css'
import './globals.css'
import Providers from '@/providers'
import MainLayout from '@/templates/MainLayout'
import Sidebar from '@/organisms/Sidebar'

export const metadata: Metadata = {
  title: 'Chilean Marine Seismic Lines',
  description: 'Database of marine seismic surveys along the Chilean subduction zone (1987–2025)',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">
        <Providers>
          <MainLayout sidebar={<Sidebar />}>{children}</MainLayout>
        </Providers>
      </body>
    </html>
  )
}
