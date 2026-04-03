import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { resumeApi } from '../services/api';
import toast from 'react-hot-toast';
import { Upload, Trash2, Star, FileText } from 'lucide-react';
import clsx from 'clsx';

export default function ResumesPage() {
  const [showUpload, setShowUpload] = useState(false);
  const [name, setName] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data: resumes, isLoading } = useQuery({
    queryKey: ['resumes'],
    queryFn: () => resumeApi.list().then((r) => r.data),
  });

  const uploadMutation = useMutation({
    mutationFn: ({ file, name: n, def }: { file: File; name: string; def: boolean }) =>
      resumeApi.upload(n, file, def),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
      toast.success('Resume uploaded!');
      setName('');
      setIsDefault(false);
      setShowUpload(false);
      if (fileRef.current) fileRef.current.value = '';
    },
    onError: () => toast.error('Upload failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => resumeApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
      toast.success('Resume deleted');
    },
  });

  const setDefaultMutation = useMutation({
    mutationFn: (id: string) => resumeApi.setDefault(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['resumes'] });
      toast.success('Default resume updated');
    },
  });

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file || !name) return;
    uploadMutation.mutate({ file, name, def: isDefault });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Resumes</h1>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Upload size={18} />
          Upload Resume
        </button>
      </div>

      {/* Upload Form */}
      {showUpload && (
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-6">
          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Resume Name</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Software Engineer Resume"
                className="mt-1 block w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">File (PDF, DOC, DOCX)</label>
              <input
                type="file"
                ref={fileRef}
                required
                accept=".pdf,.doc,.docx"
                className="mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
              />
            </div>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={isDefault}
                onChange={(e) => setIsDefault(e.target.checked)}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700">Set as default resume</span>
            </label>
            <button
              type="submit"
              disabled={uploadMutation.isPending}
              className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors"
            >
              {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
            </button>
          </form>
        </div>
      )}

      {/* Resumes List */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading && <p className="text-gray-500 col-span-full">Loading...</p>}
        {resumes?.length === 0 && (
          <p className="text-gray-500 col-span-full text-center py-8">
            No resumes uploaded yet.
          </p>
        )}
        {resumes?.map((resume) => (
          <div
            key={resume.id}
            className={clsx(
              'bg-white rounded-xl p-5 shadow-sm border',
              resume.is_default ? 'border-primary-300' : 'border-gray-100'
            )}
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <FileText size={20} className="text-primary-500" />
                <h3 className="font-medium text-sm">{resume.name}</h3>
              </div>
              {resume.is_default && (
                <span className="flex items-center gap-1 text-xs text-primary-600 bg-primary-50 px-2 py-1 rounded">
                  <Star size={12} fill="currentColor" />
                  Default
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 mb-4">
              {resume.file_type.toUpperCase()} &middot;{' '}
              {new Date(resume.created_at).toLocaleDateString()}
            </p>
            <div className="flex items-center gap-2">
              {!resume.is_default && (
                <button
                  onClick={() => setDefaultMutation.mutate(resume.id)}
                  className="text-xs px-3 py-1.5 text-primary-600 hover:bg-primary-50 rounded transition-colors"
                >
                  Set Default
                </button>
              )}
              <button
                onClick={() => deleteMutation.mutate(resume.id)}
                className="text-xs px-3 py-1.5 text-red-600 hover:bg-red-50 rounded transition-colors flex items-center gap-1"
              >
                <Trash2 size={12} />
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
