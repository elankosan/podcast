'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { api, Podcast } from '../lib/api';

export default function DashboardPage() {
  const [podcasts, setPodcasts] = useState<Podcast[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.podcasts.list()
      .then(setPodcasts)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <main className="p-8">Loading...</main>;
  if (error) return <main className="p-8 text-red-600">Error: {error}</main>;

  return (
    <main className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <Link href="/podcasts/new" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          + New Podcast
        </Link>
      </div>

      <h2 className="text-xl font-semibold mb-4">Your Podcasts</h2>
      {podcasts.length === 0 ? (
        <p className="text-gray-600">No podcasts yet. Create your first one!</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {podcasts.map((podcast) => (
            <Link
              key={podcast.id}
              href={`/podcasts/${podcast.id}`}
              className="block border rounded-lg p-4 hover:shadow-md transition"
            >
              <h3 className="text-lg font-semibold">{podcast.title}</h3>
              <p className="text-gray-600 text-sm mt-1">{podcast.description}</p>
              <div className="mt-3 flex gap-2 text-xs text-gray-500">
                <span className="bg-gray-100 px-2 py-1 rounded">{podcast.language}</span>
                {podcast.target_languages.map((lang) => (
                  <span key={lang} className="bg-gray-100 px-2 py-1 rounded">{lang}</span>
                ))}
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
