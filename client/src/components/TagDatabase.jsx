import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Search, Plus, Upload, RefreshCw, ChevronDown, ChevronUp,
  CheckCircle, XCircle, Edit2, X, Check, Loader2
} from 'lucide-react'
import { getTags, createTag, updateTag, importTagsCsv } from '../utils/api'
import { formatDateShort } from '../utils/helpers'

const DISCIPLINES = ['Mechanical', 'Electrical', 'Instrumentation', 'Piping', 'Civil', 'Process']

function AddTagModal({ onClose, onCreate }) {
  const [form, setForm] = useState({
    tag_number: '', tag_description: '', discipline: '', status: 'Active', created_by: 'admin'
  })
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.tag_number.trim()) return toast.error('Tag number is required')
    setLoading(true)
    try {
      await onCreate(form)
      toast.success(`Tag ${form.tag_number.toUpperCase()} created`)
      onClose()
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to create tag'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-lg text-gray-900">Add New Tag</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tag Number <span className="text-red-500">*</span>
            </label>
            <input
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono
                         focus:outline-none focus:ring-2 focus:ring-navy-500"
              placeholder="e.g. 10-P-105A"
              value={form.tag_number}
              onChange={e => setForm({...form, tag_number: e.target.value.toUpperCase()})}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-navy-500"
              placeholder="Equipment description"
              value={form.tag_description}
              onChange={e => setForm({...form, tag_description: e.target.value})}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Discipline</label>
              <select
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-navy-500"
                value={form.discipline}
                onChange={e => setForm({...form, discipline: e.target.value})}
              >
                <option value="">— Select —</option>
                {DISCIPLINES.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-navy-500"
                value={form.status}
                onChange={e => setForm({...form, status: e.target.value})}
              >
                <option>Active</option>
                <option>Void</option>
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Created By</label>
            <input
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm
                         focus:outline-none focus:ring-2 focus:ring-navy-500"
              placeholder="Your name"
              value={form.created_by}
              onChange={e => setForm({...form, created_by: e.target.value})}
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button type="button" className="btn-secondary flex-1" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary flex-1" disabled={loading}>
              {loading ? <Loader2 size={16} className="animate-spin mx-auto" /> : 'Create Tag'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function InlineStatusToggle({ tag, onUpdate }) {
  const [loading, setLoading] = useState(false)

  async function toggle() {
    setLoading(true)
    try {
      const newStatus = tag.status === 'Active' ? 'Void' : 'Active'
      await onUpdate(tag.id, { status: newStatus })
      toast.success(`${tag.tag_number} → ${newStatus}`)
    } catch {
      toast.error('Failed to update status')
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={toggle}
      disabled={loading}
      title={`Toggle to ${tag.status === 'Active' ? 'Void' : 'Active'}`}
      className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold transition-all
        ${tag.status === 'Active'
          ? 'bg-green-100 text-green-700 hover:bg-green-200'
          : 'bg-amber-100 text-amber-700 hover:bg-amber-200'
        } ${loading ? 'opacity-60 cursor-wait' : 'cursor-pointer'}`}
    >
      {loading
        ? <Loader2 size={12} className="animate-spin" />
        : tag.status === 'Active'
          ? <><CheckCircle size={12} /> Active</>
          : <><XCircle size={12} /> Void</>
      }
    </button>
  )
}

export default function TagDatabase() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [discipline, setDiscipline] = useState('')
  const [status, setStatus] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [sortKey, setSortKey] = useState('tag_number')
  const [sortAsc, setSortAsc] = useState(true)
  const csvRef = useRef()

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['tags', search, discipline, status],
    queryFn: () => getTags({ search, discipline: discipline || undefined, status: status || undefined }),
  })

  const createMut = useMutation({
    mutationFn: createTag,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tags'] }),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, data }) => updateTag(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tags'] }),
  })

  const importMut = useMutation({
    mutationFn: importTagsCsv,
    onSuccess: (res) => {
      toast.success(`Imported ${res.created} tags (${res.skipped} skipped)`)
      qc.invalidateQueries({ queryKey: ['tags'] })
    },
    onError: () => toast.error('Import failed'),
  })

  async function handleCsvUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    importMut.mutate(fd)
    e.target.value = ''
  }

  const tags = data?.tags || []
  const total = data?.total || 0

  const sorted = [...tags].sort((a, b) => {
    const va = a[sortKey] || ''
    const vb = b[sortKey] || ''
    return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va))
  })

  function toggleSort(key) {
    if (sortKey === key) setSortAsc(!sortAsc)
    else { setSortKey(key); setSortAsc(true) }
  }

  function SortIcon({ col }) {
    if (sortKey !== col) return <ChevronDown size={12} className="text-gray-300" />
    return sortAsc
      ? <ChevronUp size={12} className="text-gray-600" />
      : <ChevronDown size={12} className="text-gray-600" />
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5">
      {showAdd && (
        <AddTagModal onClose={() => setShowAdd(false)} onCreate={createTag} />
      )}

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Central Tag Database</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {total} tag{total !== 1 ? 's' : ''} · Master register of all equipment tags
          </p>
        </div>
        <div className="flex gap-2">
          <button
            className="btn-secondary flex items-center gap-2 text-sm"
            onClick={() => csvRef.current.click()}
            disabled={importMut.isPending}
          >
            {importMut.isPending ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />}
            Import CSV
          </button>
          <input ref={csvRef} type="file" accept=".csv" className="hidden" onChange={handleCsvUpload} />
          <button
            className="btn-primary flex items-center gap-2 text-sm"
            onClick={() => setShowAdd(true)}
          >
            <Plus size={15} /> Add Tag
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md text-sm
                       focus:outline-none focus:ring-2 focus:ring-navy-500"
            placeholder="Search tag number or description…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-500"
          value={discipline}
          onChange={e => setDiscipline(e.target.value)}
        >
          <option value="">All Disciplines</option>
          {DISCIPLINES.map(d => <option key={d}>{d}</option>)}
        </select>
        <select
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-navy-500"
          value={status}
          onChange={e => setStatus(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="Active">Active</option>
          <option value="Void">Void</option>
        </select>
        <button className="btn-secondary flex items-center gap-1 text-sm" onClick={() => refetch()}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                {[
                  { key: 'tag_number', label: 'Tag Number' },
                  { key: 'tag_description', label: 'Description' },
                  { key: 'discipline', label: 'Discipline' },
                  { key: 'status', label: 'Status' },
                  { key: 'created_at', label: 'Created' },
                  { key: 'voided_at', label: 'Voided' },
                  { key: 'created_by', label: 'By' },
                ].map(col => (
                  <th
                    key={col.key}
                    className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide cursor-pointer select-none hover:text-gray-700"
                    onClick={() => toggleSort(col.key)}
                  >
                    <span className="flex items-center gap-1">
                      {col.label} <SortIcon col={col.key} />
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-gray-400">
                    <Loader2 size={24} className="animate-spin mx-auto" />
                  </td>
                </tr>
              ) : sorted.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-gray-400">
                    No tags found.
                  </td>
                </tr>
              ) : (
                sorted.map(tag => (
                  <tr
                    key={tag.id}
                    className={`hover:bg-gray-50 transition-colors ${tag.status === 'Void' ? 'opacity-70' : ''}`}
                  >
                    <td className="px-4 py-3 font-mono font-semibold text-navy-800 whitespace-nowrap">
                      {tag.tag_number}
                    </td>
                    <td className="px-4 py-3 text-gray-700 max-w-xs">
                      {tag.tag_description || <span className="text-gray-300 italic">—</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{tag.discipline || '—'}</td>
                    <td className="px-4 py-3">
                      <InlineStatusToggle
                        tag={tag}
                        onUpdate={(id, data) => updateMut.mutateAsync({ id, data })}
                      />
                    </td>
                    <td className="px-4 py-3 text-gray-400 whitespace-nowrap text-xs">
                      {formatDateShort(tag.created_at)}
                    </td>
                    <td className="px-4 py-3 text-amber-600 whitespace-nowrap text-xs">
                      {tag.voided_at ? formatDateShort(tag.voided_at) : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{tag.created_by || '—'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        {total > 200 && (
          <div className="px-5 py-3 border-t border-gray-100 text-xs text-gray-400 text-right">
            Showing first 200 of {total}. Use search/filter to narrow results.
          </div>
        )}
      </div>

      {/* CSV template hint */}
      <div className="text-xs text-gray-400 flex items-start gap-1">
        <span className="font-semibold">CSV format:</span>
        tag_number, tag_description, discipline, status, created_by
      </div>
    </div>
  )
}
