import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { applicationApi } from '../services/api';
import toast from 'react-hot-toast';
import { RefreshCw, XCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';
import type { Application, ApplicationLog } from '../types';
import { formatDistanceToNow } from 'date-fns';

const statusColors: Record<string, string> = {
  queued: 'bg-yellow-100 text-yellow-800',
  in_progress: 'bg-purple-100 text-purple-800',
  submitted: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  captcha_required: 'bg-orange-100 text-orange-800',
  retrying: 'bg-blue-100 text-blue-800',
  cancelled: 'bg-gray-100 text-gray-800',
};

function ApplicationRow({ app }: { app: Application }) {
  const [expanded, setExpanded] = useState(false);
  const queryClient = useQueryClient();

  const { data: logs } = useQuery({
    queryKey: ['applicationLogs', app.id],
    queryFn: () => applicationApi.getLogs(app.id).then((r) => r.data),
    enabled: expanded,
  });

  const retryMutation = useMutation({
    mutationFn: () => applicationApi.retry(app.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      toast.success('Retry queued');
    },
    onError: () => toast.error('Retry failed'),
  });

  const cancelMutation = useMutation({
    mutationFn: () => applicationApi.cancel(app.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      toast.success('Application cancelled');
    },
    onError: () => toast.error('Cancel failed'),
  });

  const canRetry = ['failed', 'captcha_required'].includes(app.status) && app.retry_count < app.max_retries;
  const canCancel = ['queued', 'in_progress', 'retrying'].includes(app.status);

  return (
    <div className="border-b border-gray-100 last:border-0">
      <div
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm">{app.job_id}</p>
          <p className="text-xs text-gray-500">
            {formatDistanceToNow(new Date(app.created_at), { addSuffix: true })}
            {app.retry_count > 0 && ` · Retries: ${app.retry_count}/${app.max_retries}`}
          </p>
          {app.error_message && (
            <p className="text-xs text-red-500 mt-1 truncate">{app.error_message}</p>
          )}
        </div>
        <div className="flex items-center gap-3 ml-4">
          <span
            className={clsx(
              'px-3 py-1 rounded-full text-xs font-medium',
              statusColors[app.status]
            )}
          >
            {app.status.replace('_', ' ')}
          </span>
          {canRetry && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                retryMutation.mutate();
              }}
              className="p-1.5 text-blue-600 hover:bg-blue-50 rounded"
              title="Retry"
            >
              <RefreshCw size={16} />
            </button>
          )}
          {canCancel && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                cancelMutation.mutate();
              }}
              className="p-1.5 text-red-600 hover:bg-red-50 rounded"
              title="Cancel"
            >
              <XCircle size={16} />
            </button>
          )}
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {/* Logs */}
      {expanded && (
        <div className="px-4 pb-4">
          <div className="bg-gray-50 rounded-lg p-4 space-y-2">
            <h4 className="text-xs font-semibold text-gray-500 uppercase">Activity Log</h4>
            {logs?.length === 0 && (
              <p className="text-xs text-gray-400">No logs yet</p>
            )}
            {logs?.map((log: ApplicationLog) => (
              <div key={log.id} className="flex items-start gap-2 text-xs">
                <span
                  className={clsx(
                    'px-1.5 py-0.5 rounded font-medium',
                    log.level === 'error'
                      ? 'bg-red-100 text-red-700'
                      : log.level === 'warning'
                      ? 'bg-yellow-100 text-yellow-700'
                      : 'bg-blue-100 text-blue-700'
                  )}
                >
                  {log.level}
                </span>
                <span className="text-gray-600">{log.message}</span>
                <span className="text-gray-400 ml-auto whitespace-nowrap">
                  {new Date(log.created_at).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ApplicationsPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  const { data: apps, isLoading } = useQuery({
    queryKey: ['applications', statusFilter],
    queryFn: () => applicationApi.list(0, 100, statusFilter).then((r) => r.data),
  });

  const filters = [
    { label: 'All', value: undefined },
    { label: 'Queued', value: 'queued' },
    { label: 'In Progress', value: 'in_progress' },
    { label: 'Submitted', value: 'submitted' },
    { label: 'Failed', value: 'failed' },
    { label: 'CAPTCHA', value: 'captcha_required' },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Applications</h1>

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {filters.map(({ label, value }) => (
          <button
            key={label}
            onClick={() => setStatusFilter(value)}
            className={clsx(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              statusFilter === value
                ? 'bg-primary-100 text-primary-700'
                : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Applications List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading...</div>
        ) : apps?.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No applications found. Create one from the Jobs page.
          </div>
        ) : (
          apps?.map((app) => <ApplicationRow key={app.id} app={app} />)
        )}
      </div>
    </div>
  );
}
