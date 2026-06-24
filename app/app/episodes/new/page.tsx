'use client';

import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { api } from '../../lib/api';

function NewEpisodeForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const podcastId = searchParams.get('podcast') || '';

  const [title, setTitle] = useState('');
  const [vision, setVision] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const episode = await api.episodes.create(podcastId, {
        title,
        vision,
      });
      router.push(`/episodes/${episode.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="p-8 max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Create New Episode</h1>
      {error && <p className="text-red-600 mb-4">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full border rounded px-3 py-2"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Vision / Topic</label>
          <textarea
            value={vision}
            onChange={(e) => setVision(e.target.value)}
            className="w-full border rounded px-3 py-2"
            rows={4}
            placeholder="Describe the topic, angle, and key questions for this episode..."
            required
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Creating...' : 'Create Episode'}
        </button>
      </form>
    </main>
  );
}

export default function NewEpisodePage() {
  return (
    <Suspense fallback={<main className="p-8 max-w-2xl mx-auto">Loading...</main>}>
      <NewEpisodeForm />
    </Suspense>
  );
}
