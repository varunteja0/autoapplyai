import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobApi, applicationApi } from '../services/api';
import toast from 'react-hot-toast';
import { Plus, Trash2, ExternalLink, Rocket, Send } from 'lucide-react';
import clsx from 'clsx';

const platformBadges: Record<string, string> = {
  workday: 'bg-blue-100 text-blue-800',
  greenhouse: 'bg-green-100 text-green-800',
  lever: 'bg-purple-100 text-purple-800',
  taleo: 'bg-orange-100 text-orange-800',
  unknown: 'bg-gray-100 text-gray-800',
};

export default function JobsPage() {
  const [showForm, setShowForm] = useState(false);
  const [jobUrl, setJobUrl] = useState('');
  const [bulkUrls, setBulkUrls] = useState('');
  const [mode, setMode] = useState<'single' | 'bulk'>('single');
  const queryClient = useQueryClient();

  const { data: jobs, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobApi.list().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (url: string) => jobApi.create({ url }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job added!');
      setJobUrl('');
      setShowForm(false);
    },
    onError: () => toast.error('Failed to add job'),
  });

  const bulkMutation = useMutation({
    mutationFn: (urls: string[]) => jobApi.createBulk(urls),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success(`${data.data.length} jobs added!`);
      setBulkUrls('');
      setShowForm(false);
    },
    onError: () => toast.error('Failed to add jobs'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => jobApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      toast.success('Job removed');
    },
  });

  const applyAllMutation = useMutation({
    mutationFn: () => applicationApi.applyAll(),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['applicationStats'] });
      if (res.data.job_count === 0) {
        toast('No new jobs to apply to', { icon: 'ℹ️' });
      } else {
        toast.success(`Queued ${res.data.job_count} applications!`);
      }
    },
    onError: () => toast.error('Failed to queue applications'),
  });

  const applySingleMutation = useMutation({
    mutationFn: (jobId: string) => applicationApi.create({ job_id: jobId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['applicationStats'] });
      toast.success('Application queued!');
    },
    onError: () => toast.error('Failed to create application'),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === 'single') {
      createMutation.mutate(jobUrl);
    } else {
      const urls = bulkUrls
        .split('\n')
        .map((u) => u.trim())
        .filter(Boolean);
      if (urls.length > 0) bulkMutation.mutate(urls);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Jobs</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => applyAllMutation.mutate()}
            disabled={applyAllMutation.isPending || !jobs?.length}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            <Rocket size={18} />
            {applyAllMutation.isPending ? 'Queueing...' : 'Apply to All Jobs'}
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Plus size={18} />
            Add Jobs
          </button>
        </div>
      </div>

      {/* Add Job Form */}
      {showForm && (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-6">
          <div className="flex gap-4 mb-4">
            <button
              onClick={() => setMode('single')}
              className={clsx(
                'px-4 py-2 rounded-lg text-sm font-medium',
                mode === 'single' ? 'bg-primary-100 text-primary-700' : 'text-gray-600'
              )}
            >
              Single URL
            </button>
            <button
              onClick={() => setMode('bulk')}
              className={clsx(
                'px-4 py-2 rounded-lg text-sm font-medium',
                mode === 'bulk' ? 'bg-primary-100 text-primary-700' : 'text-gray-600'
              )}
            >
              Bulk Import
            </button>
          </div>
          <form onSubmit={handleSubmit}>
            {mode === 'single' ? (
              <input
                type="url"
                required
                value={jobUrl}
                onChange={(e) => setJobUrl(e.target.value)}
                placeholder="https://company.jobs/posting/12345"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            ) : (
              <textarea
                required
                value={bulkUrls}
                onChange={(e) => setBulkUrls(e.target.value)}
                placeholder="Paste one URL per line..."
                rows={5}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            )}
            <button
              type="submit"
              disabled={createMutation.isPending || bulkMutation.isPending}
              className="mt-4 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending || bulkMutation.isPending ? 'Adding...' : 'Add'}
            </button>
          </form>
        </div>
      )}

      {/* Jobs List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : jobs?.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No jobs added yet. Click &quot;Add Jobs&quot; to get started.
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {jobs?.map((job) => (
              <div key={job.id} className="p-4 flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-medium text-sm truncate">
                      {job.title || 'Untitled Job'}
                    </p>
                    <span
                      className={clsx(
                        'px-2 py-0.5 rounded text-xs font-medium',
                        platformBadges[job.platform]
                      )}
                    >
                      {job.platform}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 truncate">
                    {job.company || 'Unknown Company'} &middot;{' '}
                    {job.location || 'Location N/A'}
                  </p>
                  <p className="text-xs text-gray-400 truncate mt-0.5">{job.url}</p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => applySingleMutation.mutate(job.id)}
                    disabled={applySingleMutation.isPending}
                    className="p-2 text-green-500 hover:text-green-700 hover:bg-green-50 rounded"
                    title="Apply to this job"
                  >
                    <Send size={16} />
                  </button>
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 text-gray-400 hover:text-gray-600"
                  >
                    <ExternalLink size={16} />
                  </a>
                  <button
                    onClick={() => deleteMutation.mutate(job.id)}
                    className="p-2 text-gray-400 hover:text-red-600"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
