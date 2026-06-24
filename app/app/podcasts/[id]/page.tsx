'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { api, Podcast, Episode } from '../../lib/api';

export default function PodcastPage() {
  const params = useParams();
  const id = params.id as string;
  const [podcast, setPodcast] = useState<Podcast | null>(null);
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.podcasts.get(id),
      api.podcasts.episodes(id),
    ])
      .then(([p, e]) => {
        setPodcast(p);
        setEpisodes(e);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <main className="p-8">Loading...</main>;
  if (error) return <main className="p-8 text-red-600">Error: {error}</main>;
  if (!podcast) return <main className="p-8">Podcast not found</main>;

  return (
    <main className="p-8">
      <div className="mb-6">
        <Link href="/dashboard" className="text-blue-600 hover:underline">← Dashboard</Link>
      </div>

      <h1 className="text-3xl font-bold mb-2">{podcast.title}</h1>
      <p className="text-gray-600 mb-6">{podcast.description}</p>

      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Episodes</h2>
        <Link
          href={`/episodes/new?podcast=${podcast.id}`}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          + New Episode
        </Link>
      </div>

      {episodes.length === 0 ? (
        <p className="text-gray-600">No episodes yet. Create your first episode!</p>
      ) : (
        <div className="space-y-3">
          {episodes.map((ep) => (
            <Link
              key={ep.id}
              href={`/episodes/${ep.id}`}
              className="block border rounded-lg p-4 hover:shadow-md transition"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-semibold">{ep.title}</h3>
                  <p className="text-gray-600 text-sm mt-1">{ep.vision}</p>
                </div>
                <span className={`px-2 py-1 rounded text-xs ${statusColor(ep.status)}`}>
                  {ep.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}

function statusColor(status: string): string {
  switch (status) {
    case 'published':
      return 'bg-green-100 text-green-800';
    case 'translated':
      return 'bg-blue-100 text-blue-800';
    case 'scripted':
      return 'bg-purple-100 text-purple-800';
    case 'researching':
    case 'scripting':
    case 'translating':
      return 'bg-yellow-100 text-yellow-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}
