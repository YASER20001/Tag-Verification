import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// Tags (CTDB)
export const getTags = (params) => api.get('/tags', { params }).then(r => r.data)
export const createTag = (data) => api.post('/tags', data).then(r => r.data)
export const updateTag = (id, data) => api.put(`/tags/${id}`, data).then(r => r.data)
export const importTagsCsv = (formData) =>
  api.post('/tags/import', formData, { headers: { 'Content-Type': 'multipart/form-data' } }).then(r => r.data)
export const getTagDocuments = (tagNumber) => api.get(`/tags/${tagNumber}/documents`).then(r => r.data)

// Documents
export const uploadDocument = (formData, onProgress) =>
  api.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => onProgress && onProgress(Math.round((e.loaded / e.total) * 100)),
  }).then(r => r.data)
export const getReport = (docId) => api.get(`/documents/${docId}/report`).then(r => r.data)
export const approveDocument = (docId, formData) =>
  api.post(`/documents/${docId}/approve`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)

// Relationships
export const createRelationships = (documentId) =>
  api.post('/relationships/create', { document_id: documentId }).then(r => r.data)
export const getImpact = (tagNumber) => api.get(`/relationships/impact/${tagNumber}`).then(r => r.data)

// Dashboard
export const getDashboardStats = () => api.get('/dashboard/stats').then(r => r.data)
export const getRecentDocs = () => api.get('/dashboard/recent').then(r => r.data)
export const getAlerts = () => api.get('/dashboard/alerts').then(r => r.data)

export default api
