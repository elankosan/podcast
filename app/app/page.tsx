import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen p-8">
      <h1 className="text-4xl font-bold mb-4">Multi-Lingual Podcast Studio</h1>
      <p className="text-lg text-gray-600">
        Intelligent podcast preparation and translation platform.
      </p>
      <div className="mt-8">
        <Link href="/dashboard" className="bg-blue-600 text-white px-6 py-3 rounded hover:bg-blue-700">
          Go to Dashboard
        </Link>
      </div>
    </main>
  )
}
