'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { api, Episode } from '../../lib/api';

export default function EpisodePage() {
  const params = useParams();
  const id = params.id as string;
  const [episode, setEpisode] = useState<Episode | null>(null);
  const [activeTab, setActiveTab] = useState<'research' | 'script' | 'translations'>('research');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [researchData, setResearchData] = useState<any>(null);
  const [scriptData, setScriptData] = useState<any>(null);
  const [translationsData, setTranslationsData] = useState<any>(null);

  useEffect(() => {
    if (!id) return;
    api.episodes.get(id)
      .then(setEpisode)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  async function triggerResearch() {
    setActionLoading(true);
    try {
      const res = await api.episodes.research(id);
      setResearchData(res);
      setEpisode((prev) => prev ? { ...prev, status: 'researching' } : prev);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function triggerScript() {
    setActionLoading(true);
    try {
      const res = await api.episodes.script(id);
      setScriptData(res);
      setEpisode((prev) => prev ? { ...prev, status: 'scripting' } : prev);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function triggerTranslation(lang: string) {
    setActionLoading(true);
    try {
      const res = await api.episodes.translate(id, lang);
      setTranslationsData(res);
      setEpisode((prev) => prev ? { ...prev, status: 'translating' } : prev);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) return <main className="p-8">Loading...</main>;
  if (error) return <main className="p-8 text-red-600">Error: {error}</main>;
  if (!episode) return <main className="p-8">Episode not found</main>;

  return (
    <main className="p-8">
      <div className="mb-6">
        <Link href={`/podcasts/${episode.podcast_id}`} className="text-blue-600 hover:underline">
          ← Back to Podcast
        </Link>
      </div>

      <div className="flex justify-between items-start mb-6">
        <div>
          <h1 className="text-3xl font-bold">{episode.title}</h1>
          <p className="text-gray-600 mt-2">{episode.vision}</p>
        </div>
        <span className={`px-3 py-1 rounded text-sm ${statusColor(episode.status)}`}>
          {episode.status}
        </span>
      </div>

      <div className="border-b mb-6">
        <nav className="flex gap-6">
          {(['research', 'script', 'translations'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-2 px-1 capitalize ${
                activeTab === tab
                  ? 'border-b-2 border-blue-600 text-blue-600 font-medium'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab}
            </button>
          ))}
        </nav>
      </div>

      {activeTab === 'research' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Research</h2>
            <button
              onClick={triggerResearch}
              disabled={actionLoading}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {actionLoading ? 'Working...' : '🔍 Research Topic'}
            </button>
          </div>
          {researchData?.result?.output?.synthesis && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold mb-2">Synthesis</h3>
              <div className="whitespace-pre-wrap text-sm">{researchData.result.output.synthesis}</div>
            </div>
          )}
          {researchData?.result?.output?.structured && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold mb-2">Structured Findings</h3>
              <pre className="text-xs overflow-auto">{JSON.stringify(researchData.result.output.structured, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {activeTab === 'script' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Script</h2>
            <button
              onClick={triggerScript}
              disabled={actionLoading}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {actionLoading ? 'Working...' : '📝 Generate Script'}
            </button>
          </div>
          {scriptData?.result?.output?.script_enhanced && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold mb-2">Enhanced Script</h3>
              <div className="whitespace-pre-wrap text-sm font-mono">{scriptData.result.output.script_enhanced}</div>
            </div>
          )}
          {scriptData?.result?.output?.segments && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold mb-2">Segments</h3>
              <ul className="text-sm space-y-1">
                {scriptData.result.output.segments.map((seg: any, i: number) => (
                  <li key={i} className="border-b py-1">{seg.name}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {activeTab === 'translations' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Translations</h2>
            <div className="flex gap-2">
              {['fr', 'es', 'ta', 'de'].map((lang) => (
                <button
                  key={lang}
                  onClick={() => triggerTranslation(lang)}
                  disabled={actionLoading}
                  className="bg-blue-600 text-white px-3 py-2 rounded hover:bg-blue-700 disabled:opacity-50 text-sm uppercase"
                >
                  {lang}
                </button>
              ))}
            </div>
          </div>
          {translationsData?.result?.output?.translation_polished && (
            <div className="bg-gray-50 p-4 rounded-lg">
              <h3 className="font-semibold mb-2">
                {translationsData.result.output.language_name} Translation
              </h3>
              <div className="whitespace-pre-wrap text-sm font-mono">
                {translationsData.result.output.translation_polished}
              </div>
            </div>
          )}
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
