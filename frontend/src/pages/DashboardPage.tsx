import { useQuery } from '@tanstack/react-query';
import { applicationApi } from '../services/api';
import { useAuthStore } from '../hooks/useAuth';
import {
  Send,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import clsx from 'clsx';

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);

  const { data: stats, isLoading } = useQuery({
    queryKey: ['applicationStats'],
    queryFn: () => applicationApi.getStats().then((r) => r.data),
  });

  const { data: recentApps } = useQuery({
    queryKey: ['recentApplications'],
    queryFn: () => applicationApi.list(0, 5).then((r) => r.data),
  });

  const statCards = [
    { label: 'Total', value: stats?.total ?? 0, icon: Send, color: 'bg-blue-500' },
    { label: 'Queued', value: stats?.queued ?? 0, icon: Clock, color: 'bg-yellow-500' },
    { label: 'In Progress', value: stats?.in_progress ?? 0, icon: Loader2, color: 'bg-purple-500' },
    { label: 'Submitted', value: stats?.submitted ?? 0, icon: CheckCircle2, color: 'bg-green-500' },
    { label: 'Failed', value: stats?.failed ?? 0, icon: XCircle, color: 'bg-red-500' },
    { label: 'CAPTCHA', value: stats?.captcha_required ?? 0, icon: AlertTriangle, color: 'bg-orange-500' },
  ];

  const statusColors: Record<string, string> = {
    queued: 'bg-yellow-100 text-yellow-800',
    in_progress: 'bg-purple-100 text-purple-800',
    submitted: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    captcha_required: 'bg-orange-100 text-orange-800',
    retrying: 'bg-blue-100 text-blue-800',
    cancelled: 'bg-gray-100 text-gray-800',
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.full_name?.split(' ')[0]}
        </h1>
        <p className="text-gray-600 mt-1">
          Today&apos;s applications: {user?.daily_application_count ?? 0} / 10,000
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {statCards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center mb-3', color)}>
              <Icon size={20} className="text-white" />
            </div>
            <p className="text-2xl font-bold">{isLoading ? '-' : value}</p>
            <p className="text-sm text-gray-500">{label}</p>
          </div>
        ))}
      </div>

      {/* Recent Applications */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100">
        <div className="p-6 border-b border-gray-100">
          <h2 className="text-lg font-semibold">Recent Applications</h2>
        </div>
        <div className="divide-y divide-gray-100">
          {recentApps?.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              No applications yet. Add some jobs to get started!
            </div>
          )}
          {recentApps?.map((app) => (
            <div key={app.id} className="p-4 flex items-center justify-between">
              <div>
                <p className="font-medium text-sm">{app.job_id}</p>
                <p className="text-xs text-gray-500">
                  {new Date(app.created_at).toLocaleDateString()}
                </p>
              </div>
              <span
                className={clsx(
                  'px-3 py-1 rounded-full text-xs font-medium',
                  statusColors[app.status] || 'bg-gray-100 text-gray-800'
                )}
              >
                {app.status.replace('_', ' ')}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
