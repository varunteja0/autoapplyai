export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_verified: boolean;
  daily_application_count: number;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Job {
  id: string;
  url: string;
  title: string | null;
  company: string | null;
  location: string | null;
  description: string | null;
  platform: 'workday' | 'greenhouse' | 'lever' | 'taleo' | 'unknown';
  status: 'pending' | 'detected' | 'ready' | 'expired' | 'error';
  platform_job_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  resume_id: string | null;
  status: ApplicationStatus;
  retry_count: number;
  max_retries: number;
  error_message: string | null;
  submitted_at: string | null;
  celery_task_id: string | null;
  custom_answers: Record<string, string> | null;
  created_at: string;
  updated_at: string;
}

export type ApplicationStatus =
  | 'queued'
  | 'in_progress'
  | 'submitted'
  | 'failed'
  | 'captcha_required'
  | 'retrying'
  | 'cancelled';

export interface ApplicationStats {
  total: number;
  queued: number;
  in_progress: number;
  submitted: number;
  failed: number;
  captcha_required: number;
}

export interface ApplicationLog {
  id: string;
  application_id: string;
  level: string;
  message: string;
  details: Record<string, unknown> | null;
  screenshot_url: string | null;
  created_at: string;
}

export interface Resume {
  id: string;
  user_id: string;
  name: string;
  file_path: string;
  file_type: string;
  is_default: boolean;
  parsed_data: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface UserProfile {
  id: string;
  user_id: string;
  phone: string | null;
  address_line1: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  country: string | null;
  linkedin_url: string | null;
  github_url: string | null;
  portfolio_url: string | null;
  years_of_experience: number | null;
  current_title: string | null;
  current_company: string | null;
  work_authorization: string | null;
  requires_sponsorship: boolean | null;
  stored_answers: Record<string, string> | null;
  skills: string[] | null;
  salary_expectation: string | null;
  created_at: string;
  updated_at: string;
}
