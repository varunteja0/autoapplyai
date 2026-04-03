import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { userApi } from '../services/api';
import toast from 'react-hot-toast';
import type { UserProfile } from '../types';

export default function ProfilePage() {
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: () => userApi.getProfile().then((r) => r.data),
  });

  const [form, setForm] = useState<Partial<UserProfile>>({});

  useEffect(() => {
    if (profile) setForm(profile);
  }, [profile]);

  const mutation = useMutation({
    mutationFn: (data: Partial<UserProfile>) => userApi.upsertProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      toast.success('Profile saved!');
    },
    onError: () => toast.error('Failed to save profile'),
  });

  const handleChange = (field: string, value: string | number | boolean | null) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(form);
  };

  if (isLoading) return <div className="text-gray-500">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Profile & Autofill Data</h1>
      <form onSubmit={handleSubmit} className="max-w-2xl space-y-8">
        {/* Contact Info */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Contact Information</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Phone" value={form.phone ?? ''} onChange={(v) => handleChange('phone', v)} />
            <Field label="Country" value={form.country ?? 'United States'} onChange={(v) => handleChange('country', v)} />
            <Field label="Address" value={form.address_line1 ?? ''} onChange={(v) => handleChange('address_line1', v)} className="col-span-2" />
            <Field label="City" value={form.city ?? ''} onChange={(v) => handleChange('city', v)} />
            <Field label="State" value={form.state ?? ''} onChange={(v) => handleChange('state', v)} />
            <Field label="Zip Code" value={form.zip_code ?? ''} onChange={(v) => handleChange('zip_code', v)} />
          </div>
        </section>

        {/* Professional Info */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Professional Information</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Current Title" value={form.current_title ?? ''} onChange={(v) => handleChange('current_title', v)} />
            <Field label="Current Company" value={form.current_company ?? ''} onChange={(v) => handleChange('current_company', v)} />
            <Field
              label="Years of Experience"
              value={String(form.years_of_experience ?? '')}
              onChange={(v) => handleChange('years_of_experience', v ? parseInt(v, 10) : null)}
              type="number"
            />
            <Field label="Salary Expectation" value={form.salary_expectation ?? ''} onChange={(v) => handleChange('salary_expectation', v)} />
          </div>
        </section>

        {/* Links */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Links</h2>
          <div className="grid grid-cols-1 gap-4">
            <Field label="LinkedIn URL" value={form.linkedin_url ?? ''} onChange={(v) => handleChange('linkedin_url', v)} />
            <Field label="GitHub URL" value={form.github_url ?? ''} onChange={(v) => handleChange('github_url', v)} />
            <Field label="Portfolio URL" value={form.portfolio_url ?? ''} onChange={(v) => handleChange('portfolio_url', v)} />
          </div>
        </section>

        {/* Work Authorization */}
        <section>
          <h2 className="text-lg font-semibold mb-4">Work Authorization</h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Work Authorization" value={form.work_authorization ?? ''} onChange={(v) => handleChange('work_authorization', v)} placeholder="e.g., US Citizen, Green Card" />
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Requires Sponsorship</label>
              <select
                value={form.requires_sponsorship === true ? 'yes' : form.requires_sponsorship === false ? 'no' : ''}
                onChange={(e) => handleChange('requires_sponsorship', e.target.value === 'yes' ? true : e.target.value === 'no' ? false : null)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                <option value="">Select...</option>
                <option value="no">No</option>
                <option value="yes">Yes</option>
              </select>
            </div>
          </div>
        </section>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="px-8 py-3 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
        >
          {mutation.isPending ? 'Saving...' : 'Save Profile'}
        </button>
      </form>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  className,
}: {
  label: string;
  value: string;
  onChange: (val: string) => void;
  type?: string;
  placeholder?: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
      />
    </div>
  );
}
