import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import { ReactNode } from 'react'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Multi-Lingual Podcast Studio',
  description: 'Intelligent podcast preparation studio',
}

export default function RootLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav className="bg-gray-900 text-white p-4">
          <div className="max-w-7xl mx-auto flex justify-between items-center">
            <Link href="/" className="text-xl font-bold">Podcast Studio</Link>
            <div className="space-x-4">
              <Link href="/dashboard" className="hover:text-gray-300">Dashboard</Link>
              <Link href="/login" className="hover:text-gray-300">Login</Link>
            </div>
          </div>
        </nav>
        {children}
      </body>
    </html>
  )
}
