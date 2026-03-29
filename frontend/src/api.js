import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

const api = axios.create({ baseURL: BASE })

export const getStocks = () => api.get('/stocks').then(r => r.data)
export const updateStock = (ticker, data) => api.put(`/stocks/${ticker}`, data).then(r => r.data)
export const createStock = (data) => api.post('/stocks', data).then(r => r.data)
export const deleteStock = (ticker) => api.delete(`/stocks/${ticker}`).then(r => r.data)

export const getPortfolioSummary = () => api.get('/portfolio/summary').then(r => r.data)
export const getSectorWeights = () => api.get('/portfolio/sector-weights').then(r => r.data)
export const updateCash = (cash_balance) => api.put('/portfolio/cash', { cash_balance }).then(r => r.data)

export const getTransactions = () => api.get('/transactions').then(r => r.data)
export const createTransaction = (data) => api.post('/transactions', data).then(r => r.data)

export const refreshPrices = () => api.get('/prices/refresh').then(r => r.data)
export const getPrice = (ticker) => api.get(`/prices/${ticker}`).then(r => r.data)

export const getSignals = () => api.get('/signals').then(r => r.data)
export const getRebalance = () => api.get('/portfolio/rebalance').then(r => r.data)
export const getSellScenario = (ticker) => api.get(`/stocks/${ticker}/sell-scenario`).then(r => r.data)

export const getAnalysis = (ticker) => api.get(`/analysis/${ticker}`).then(r => r.data)
export const runAnalysis = (ticker) => api.post(`/analysis/${ticker}`).then(r => r.data)
export const runBatchAnalysis = () => api.post('/analysis/batch').then(r => r.data)
