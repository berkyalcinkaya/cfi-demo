export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export const apiUrl = (path: string) => `${API_BASE}${path}`

// Mirrors backend/api/schemas.py
export type BBox = { ul_x: number; ul_y: number; lr_x: number; lr_y: number }

export type Prediction = {
  score: number
  model_version: string
  is_fabricated: boolean
}

export type PloidyPrediction = Prediction & {
  ploidy: 'euploid' | 'aneuploid' | 'mosaic'
}

export type Thumbnail = { timepoint: number; url: string }

export type EmbryoCard = {
  label: string
  num_timepoints: number
  date_seeded: string
  well: number | null
  thumbnail: Thumbnail | null
  ploidy: PloidyPrediction | null
  live_birth: Prediction | null
}

export type Patient = {
  id: string
  name: string
  date_of_birth: string
  age: number
  office: string
  embryos: EmbryoCard[]
}

export type PatientSummary = {
  id: string
  name: string
  age: number
  num_embryos: number
}

export type FocalImage = { focal_depth: number; url: string }

export type FocalStack = {
  patient_id: string
  embryo: string
  timepoint: number
  num_timepoints: number
  stage: string | null
  bbox: BBox | null
  focal_stack: FocalImage[]
}

export type TimelinePoint = { timepoint: number; stage: string }

export type Milestone = {
  stage: string
  first_seen: number
  frames_at_stage: number
}

export type Timeline = {
  patient_id: string
  embryo: string
  num_timepoints: number
  stream: TimelinePoint[]
  milestones: Milestone[]
}

export type ComparisonEmbryo = {
  label: string
  num_timepoints: number
  ploidy: 'euploid' | 'aneuploid' | 'mosaic' | null
  live_birth_score: number | null
  stream: TimelinePoint[]
  milestones: Milestone[]
}

export type Comparison = {
  patient_id: string
  embryos: ComparisonEmbryo[]
}

// Ploidy is reported as three classes; the demo UI folds the uncertain
// "mosaic" call into "aneuploid" (abnormal) and shows a two-state indicator.
export type PloidyDisplay = 'euploid' | 'aneuploid'
export function foldPloidy(p: string | null | undefined): PloidyDisplay | null {
  if (!p) return null
  return p === 'euploid' ? 'euploid' : 'aneuploid'
}

export type RunStatus = 'succeeded' | 'failed' | 'running'

export type IngestRun = {
  run_id: string
  patient_external_id: string
  embryo_label: string
  model_version: string
  tp_start: number | null
  tp_end: number | null
  status: RunStatus
  rows_written: number
  started_at: string
  finished_at: string | null
  is_fabricated: boolean
}

export type EvictedEmbryo = {
  patient_external_id: string
  patient_name: string
  embryo_label: string
  evicted_at: string
  num_images: number
  source_hint: string
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path))
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} on ${path}`)
  return res.json()
}

export const api = {
  listPatients: () => fetchJson<PatientSummary[]>(`/patients`),
  getPatient: (id: string) => fetchJson<Patient>(`/patients/${id}`),
  getFocalStack: (patientId: string, label: string, tp: number) =>
    fetchJson<FocalStack>(
      `/patients/${patientId}/embryos/${label}/timepoints/${tp}`,
    ),
  getTimeline: (patientId: string, label: string) =>
    fetchJson<Timeline>(`/patients/${patientId}/embryos/${label}/timeline`),
  getComparison: (patientId: string) =>
    fetchJson<Comparison>(`/patients/${patientId}/timelines`),
  getIngestRuns: () => fetchJson<IngestRun[]>(`/admin/ingest-runs`),
  getEvicted: () => fetchJson<EvictedEmbryo[]>(`/admin/evicted`),
}

// --- Mock client-only auth gate (demo only; no backend/JWT/session). ---
const AUTH_FLAG = 'embpred_auth'
const AUTH_USER = 'embpred_user'

export const auth = {
  isAuthed: () => Boolean(localStorage.getItem(AUTH_FLAG)),
  signIn: (email: string) => {
    localStorage.setItem(AUTH_FLAG, '1')
    localStorage.setItem(AUTH_USER, email)
  },
  signOut: () => {
    localStorage.removeItem(AUTH_FLAG)
    localStorage.removeItem(AUTH_USER)
  },
  user: () => localStorage.getItem(AUTH_USER) ?? '',
}
