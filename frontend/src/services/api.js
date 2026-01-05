import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Online Evaluation API
export const onlineEvaluation = {
  evaluate: async (data) => {
    const response = await api.post('/api/online/evaluate', data)
    return response.data
  },
  uploadMultimodal: async (files) => {
    const formData = new FormData()
    files.forEach((file) => {
      formData.append('files', file)
    })
    const response = await api.post('/api/online/upload-multimodal', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },
}

// Batch Evaluation API
export const batchEvaluation = {
  getMapping: async (data) => {
    const response = await api.post('/api/batch/mapping', data)
    return response.data
  },
  submit: async (data) => {
    const response = await api.post('/api/batch/submit', data)
    return response.data
  },
  evaluate: async (data) => {
    const response = await api.post('/api/batch/evaluate', data)
    return response.data
  },
}

// Performance Evaluation API
export const performanceEvaluation = {
  benchmark: async (data) => {
    const response = await api.post('/api/performance/benchmark', data)
    return response.data
  },
}

export default api
