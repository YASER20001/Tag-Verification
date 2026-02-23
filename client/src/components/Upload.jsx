import { useState, useCallback, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Upload as UploadIcon, FileText, CheckCircle, AlertTriangle,
  ChevronRight, RotateCcw, Download, Database, Loader2, X
} from 'lucide-react'
import { uploadDocument, getReport, approveDocument, createRelationships } from '../utils/api'
import VerificationReport from './VerificationReport'

const STEPS = [
  { id: 1, label: 'Drop', desc: 'Upload document' },
  { id: 2, label: 'Scan', desc: 'Extracting tags' },
  { id: 3, label: 'Report', desc: 'Verification results' },
  { id: 4, label: 'Decide', desc: 'Take action' },
]

function Stepper({ step }) {
  return (
    <div className="flex items-center gap-0 mb-8">
      {STEPS.map((s, i) => (
        <div key={s.id} className="flex items-center">
          <div className="flex flex-col items-center">
            <div
              className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all
                ${step > s.id  ? 'bg-green-500 border-green-500 text-white'
                : step === s.id ? 'bg-navy-800 border-navy-800 text-white ring-4 ring-navy-100'
                : 'bg-white border-gray-300 text-gray-400'}`}
            >
              {step > s.id ? <CheckCircle size={16} /> : s.id}
            </div>
            <div className="mt-1.5 text-center">
              <div className={`text-xs font-semibold ${step >= s.id ? 'text-navy-800' : 'text-gray-400'}`}>
                {s.label}
              </div>
              <div className="text-xs text-gray-400 hidden sm:block">{s.desc}</div>
            </div>
          </div>
          {i < STEPS.length - 1 && (
            <div className={`flex-1 h-0.5 mx-2 mb-5 ${step > s.id ? 'bg-green-400' : 'bg-gray-200'}`}
              style={{ minWidth: 32 }}
            />
          )}
        </div>
      ))}
    </div>
  )
}

export default function UploadFlow() {
  const { docId: paramDocId } = useParams()
  const navigate = useNavigate()

  const [step, setStep] = useState(paramDocId ? 3 : 1)
  const [file, setFile] = useState(null)
  const [docNumber, setDocNumber] = useState('')
  const [docTitle, setDocTitle] = useState('')
  const [docRevision, setDocRevision] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [docId, setDocId] = useState(paramDocId ? Number(paramDocId) : null)
  const [approving, setApproving] = useState(false)
  const [linking, setLinking] = useState(false)

  // Fetch report when we have a docId and are on step 3+
  const { data: reportData, isLoading: reportLoading } = useQuery({
    queryKey: ['report', docId],
    queryFn: () => getReport(docId),
    enabled: !!docId && step >= 3,
  })

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) setFile(accepted[0])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/tiff': ['.tiff', '.tif'],
    },
    maxSize: 50 * 1024 * 1024,
    multiple: false,
  })

  async function handleUpload() {
    if (!file || !docNumber.trim()) {
      toast.error('Please provide a document number and select a file.')
      return
    }
    setUploading(true)
    setStep(2)
    setUploadProgress(0)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('document_number', docNumber.trim())
      fd.append('document_title', docTitle.trim())
      fd.append('document_revision', docRevision.trim())

      const result = await uploadDocument(fd, setUploadProgress)
      setDocId(result.document.id)
      setStep(3)
      navigate(`/upload/${result.document.id}`, { replace: true })
      toast.success('Verification complete!')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Upload failed. Please try again.'
      toast.error(msg)
      setStep(1)
    } finally {
      setUploading(false)
    }
  }

  async function handleApprove(withOverride = false) {
    setApproving(true)
    try {
      const fd = new FormData()
      fd.append('approved_by', 'engineer')
      if (withOverride) fd.append('override_justification', 'Override accepted by engineer')
      await approveDocument(docId, fd)
      setStep(4)
      toast.success('Document approved to issue!')
    } catch {
      toast.error('Approval failed.')
    } finally {
      setApproving(false)
    }
  }

  async function handleLink() {
    setLinking(true)
    try {
      const result = await createRelationships(docId)
      toast.success(`Created ${result.created} tag-document relationships.`)
    } catch {
      toast.error('Failed to create relationships.')
    } finally {
      setLinking(false)
    }
  }

  function handleReset() {
    setStep(1)
    setFile(null)
    setDocNumber('')
    setDocTitle('')
    setDocRevision('')
    setDocId(null)
    setUploadProgress(0)
    navigate('/upload', { replace: true })
  }

  const summary = reportData?.summary
  const canIssue = summary?.overall_status === 'pass'
  const hasIssues = summary && summary.overall_status !== 'pass'

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Verify Document</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Upload a document to extract and verify tag numbers against the CTDB
        </p>
      </div>

      <Stepper step={step} />

      {/* ---- Step 1: Drop ---- */}
      {step === 1 && (
        <div className="card p-6 space-y-5">
          <h2 className="font-semibold text-gray-900 text-lg">Upload Document</h2>

          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors
              ${isDragActive
                ? 'border-blue-400 bg-blue-50'
                : file
                  ? 'border-green-400 bg-green-50'
                  : 'border-gray-300 bg-gray-50 hover:border-blue-300 hover:bg-blue-50'
              }`}
          >
            <input {...getInputProps()} />
            {file ? (
              <div className="flex flex-col items-center gap-3">
                <FileText size={40} className="text-green-600" />
                <div>
                  <p className="font-semibold text-green-800">{file.name}</p>
                  <p className="text-sm text-green-600">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
                <button
                  className="text-sm text-red-500 hover:text-red-700 flex items-center gap-1"
                  onClick={(e) => { e.stopPropagation(); setFile(null) }}
                >
                  <X size={14} /> Remove
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3 text-gray-500">
                <UploadIcon size={40} className="text-gray-300" />
                <div>
                  <p className="font-semibold text-gray-600">
                    {isDragActive ? 'Drop file here...' : 'Drag & drop a file, or click to browse'}
                  </p>
                  <p className="text-sm text-gray-400 mt-1">
                    PDF, PNG, JPG, TIFF up to 50 MB
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Metadata form */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Document Number <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-navy-500 font-mono"
                placeholder="e.g. P&ID-10-001"
                value={docNumber}
                onChange={(e) => setDocNumber(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Document Title</label>
              <input
                type="text"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-navy-500"
                placeholder="e.g. Feed Water System P&ID"
                value={docTitle}
                onChange={(e) => setDocTitle(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Revision</label>
              <input
                type="text"
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-navy-500"
                placeholder="e.g. A, B, 0, 1"
                value={docRevision}
                onChange={(e) => setDocRevision(e.target.value)}
              />
            </div>
          </div>

          <div className="flex justify-end">
            <button
              className="btn-primary flex items-center gap-2 px-6"
              onClick={handleUpload}
              disabled={!file || !docNumber.trim()}
            >
              Start Verification
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      )}

      {/* ---- Step 2: Scanning ---- */}
      {step === 2 && (
        <div className="card p-12 flex flex-col items-center gap-6">
          <div className="relative">
            <Loader2 size={56} className="text-navy-800 animate-spin" />
          </div>
          <div className="text-center">
            <h2 className="text-xl font-bold text-gray-900">Scanning Document…</h2>
            <p className="text-gray-500 mt-1">Extracting text and detecting tag numbers</p>
          </div>
          {uploadProgress > 0 && (
            <div className="w-full max-w-md">
              <div className="flex justify-between text-sm text-gray-500 mb-1">
                <span>Uploading</span><span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-navy-800 h-2 rounded-full transition-all duration-200"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}
          <p className="text-xs text-gray-400">This may take a moment for large or scanned PDFs</p>
        </div>
      )}

      {/* ---- Step 3 & 4: Report ---- */}
      {(step === 3 || step === 4) && (
        <div className="space-y-5">
          {reportLoading ? (
            <div className="card p-12 flex items-center justify-center gap-3 text-gray-500">
              <Loader2 size={24} className="animate-spin" /> Loading report…
            </div>
          ) : reportData ? (
            <>
              <VerificationReport report={reportData} />

              {/* Action Bar */}
              <div className="card p-5 flex flex-wrap gap-3 items-center justify-between">
                <div className="flex items-center gap-2">
                  {canIssue ? (
                    <span className="flex items-center gap-2 text-green-700 font-semibold text-sm">
                      <CheckCircle size={18} /> All tags valid — ready to issue
                    </span>
                  ) : (
                    <span className="flex items-center gap-2 text-amber-700 font-semibold text-sm">
                      <AlertTriangle size={18} /> Issues found — review before issuing
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    className="btn-secondary flex items-center gap-2"
                    onClick={handleReset}
                  >
                    <RotateCcw size={15} /> Correct & Recheck
                  </button>
                  <button
                    className="btn-secondary flex items-center gap-2"
                    onClick={handleLink}
                    disabled={linking}
                  >
                    {linking ? <Loader2 size={15} className="animate-spin" /> : <Database size={15} />}
                    Save Tag Links
                  </button>
                  {hasIssues && step < 4 && (
                    <button
                      className="btn-danger flex items-center gap-2"
                      onClick={() => handleApprove(true)}
                      disabled={approving}
                    >
                      {approving ? <Loader2 size={15} className="animate-spin" /> : <AlertTriangle size={15} />}
                      Override & Issue
                    </button>
                  )}
                  {(canIssue || step === 4) && step < 4 && (
                    <button
                      className="btn-primary flex items-center gap-2"
                      onClick={() => handleApprove(false)}
                      disabled={approving}
                    >
                      {approving ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle size={15} />}
                      Proceed to Issue
                    </button>
                  )}
                  {step === 4 && (
                    <span className="flex items-center gap-2 text-blue-700 font-semibold text-sm px-3 py-2 bg-blue-50 rounded-md">
                      <CheckCircle size={16} /> Document Approved
                    </span>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="card p-8 text-center text-gray-400">
              No report data. <button className="text-blue-600 underline" onClick={handleReset}>Start over.</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
