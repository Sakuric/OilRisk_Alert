export type FactorCategory = 'Supply-Demand' | 'Macro' | 'Financial' | 'Geopolitical' | 'Sentiment'

export interface FactorDetail {
  name: string
  nameZh: string
  shap: number
  category: FactorCategory
  value: number
}

export interface CategoryScore {
  category: FactorCategory
  score: number
  topFactors: FactorDetail[]
}

export const FACTOR_CATEGORIES: FactorCategory[] = [
  'Supply-Demand',
  'Macro',
  'Financial',
  'Geopolitical',
  'Sentiment',
]

export interface RadarScore {
  category: string
  categoryZh: string
  score: number
  topFactors: FactorDetail[]
}

export interface WeightConfig {
  supplyDemand: number
  macro: number
  financial: number
  geopolitical: number
  sentiment: number
}
