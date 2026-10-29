export interface HealthStatus {
  status: string;
  version: string;
  database: string;
  database_connected: boolean;
  total_runs: number;
  timestamp: string;
}

export interface DashboardSummary {
  total_records_processed: number;
  valid_records_processed: number;
  quarantined_records: number;
  golden_masters_created: number;
  exact_merges: number;
  probable_merges: number;
  manual_reviews_pending: number;
  total_runs_count: number;
  latest_run: PipelineRun | null;
  runs_by_entity: Record<string, number>;
  status_distribution: Record<string, number>;
  rejection_distribution: Record<string, number>;
}

export interface PipelineRun {
  run_id: string;
  entity_type: 'CUSTOMER' | 'PRODUCT';
  started_at: string;
  ended_at: string | null;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED';
  input_count: number;
  valid_count: number;
  quarantined_count: number;
  exact_match_count: number;
  probable_match_count: number;
  review_count: number;
  distinct_count: number;
  elapsed_seconds: number | null;
  error_summary: string | null;
}

export interface RunListResponse {
  items: PipelineRun[];
  total: number;
  page: number;
  page_size: number;
}

export interface RunTriggerRequest {
  entity_type: 'customer' | 'product';
  input_file: string;
  force_full_pairwise?: boolean;
}

export interface MasterCustomerRecord {
  master_id: string;
  first_name?: string | null;
  last_name: string;
  primary_email?: string | null;
  secondary_emails?: string[];
  primary_phone?: string | null;
  secondary_phones?: string[];
  street_address?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  tax_id?: string | null;
  date_of_birth?: string | null;
  created_at: string;
  updated_at: string;
  record_version: number;
  source_count?: number;
}

export interface MasterProductRecord {
  master_id: string;
  product_name: string;
  brand: string;
  primary_sku?: string | null;
  secondary_skus?: string[];
  primary_upc_ean?: string | null;
  category?: string | null;
  unit_price?: number | null;
  currency?: string | null;
  created_at: string;
  updated_at: string;
  record_version: number;
  source_count?: number;
}

export interface RecordListResponse<T = any> {
  entity_type: 'customer' | 'product';
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface LineageRecord {
  lineage_id: string;
  run_id: string;
  entity_type: string;
  source_system: string;
  source_record_id: string;
  master_id: string;
  decision: string;
  match_rule_id: string;
  confidence_score: number;
  merge_reasons: string[];
  created_at: string;
}

export interface MasterLineageDetail {
  master_record: Record<string, any>;
  lineage: LineageRecord[];
}

export interface ReviewItem {
  review_id: string;
  run_id: string;
  entity_type: string;
  source_system: string;
  source_record_id: string;
  candidate_master_id: string | null;
  similarity_score: number | null;
  reasons: string[];
  hard_conflicts?: string[];
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'RESOLVED';
  created_at: string;
}

export interface ReviewQueueResponse {
  items: ReviewItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface QuarantineRecordItem {
  quarantine_id: string;
  run_id: string;
  entity_type: string;
  source_system: string;
  source_record_id: string;
  raw_payload: Record<string, any>;
  rejection_reasons: Array<{
    field?: string;
    code: string;
    message: string;
    invalid_value?: any;
  }>;
  quarantined_at: string;
}

export interface DataQualitySummary {
  total_quarantined: number;
  quarantine_rate_pct: number;
  rejection_code_counts: Record<string, number>;
  rejections_by_field: Record<string, number>;
  recent_quarantines: QuarantineRecordItem[];
  total_accepted: number;
}

export interface AvailableFile {
  path: string;
  filename: string;
  size_bytes: number;
  entity_hint: string;
  is_sample: boolean;
}

export interface SettingsData {
  customer_rules: Record<string, any>;
  product_rules: Record<string, any>;
  database_path: string;
  output_directory: string;
}

