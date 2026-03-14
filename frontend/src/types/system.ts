export interface FactorsCoverage {
  total: number
  available: number
}

export interface SystemStatusVO {
  lastCollectionTime: string | null
  lastCollectionStatus: 'SUCCESS' | 'PARTIAL' | 'FAILED' | 'INIT' | 'RUNNING' | 'UNAVAILABLE'
  lastPredictionTime: string | null
  dataDate: string | null
  nextScheduled: string | null
  factorsCoverage: {
    daily: FactorsCoverage
    weekly: FactorsCoverage
    monthly: FactorsCoverage
  }
}

export interface CollectResultVO {
  status: 'success' | 'partial' | 'failed' | 'started' | 'already_running'
  message?: string
  collection?: {
    date: string
    total: number
    success: number
    failed: number
    failedFactors: string[]
    durationMs: number
  }
  prediction?: {
    score: number
    level: string
    date: string
  } | null
}
