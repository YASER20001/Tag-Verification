import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, Tag, FileText, AlertTriangle, CheckCircle, XCircle, Link2 } from 'lucide-react'
import { getImpact, getTagDocuments } from '../utils/api'
import { STATUS_CONFIG, formatDateShort } from '../utils/helpers'

const SAMPLE_TAGS = [
  '10-P-101A', '10-P-101B', '10-P-102B', '20-XV-2004',
  '10-PSV-1004B', '20-HX-302', '10-V-203', '10-TT-1004',
]

export default function ImpactAnalysis() {
  const [searchParams] = useSearchParams()
  const [tagInput, setTagInput] = useState(searchParams.get('tag') || '')
  const [activeTag, setActiveTag] = useState(searchParams.get('tag') || '')

  const { data: impact, isLoading, error } = useQuery({
    queryKey: ['impact', activeTag],
    queryFn: () => getImpact(activeTag),
    enabled: !!activeTag,
  })

  function handleSearch(e) {
    e.preventDefault()
    const v = tagInput.trim().toUpperCase()
    if (v) setActiveTag(v)
  }

  const tag = impact?.tag
  const docs = impact?.documents || []
  const hasVoidIssue = tag?.status === 'Void' && docs.length > 0

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Impact Analysis</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Find all documents referencing a tag, or assess impact of voiding a tag
        </p>
      </div>

      {/* Search */}
      <div className="card p-5">
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Tag size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              className="w-full pl-9 pr-3 py-2.5 border border-gray-300 rounded-md text-sm font-mono
                         focus:outline-none focus:ring-2 focus:ring-navy-500 uppercase"
              placeholder="Enter tag number, e.g. 10-P-101A"
              value={tagInput}
              onChange={e => setTagInput(e.target.value.toUpperCase())}
            />
          </div>
          <button type="submit" className="btn-primary flex items-center gap-2 px-5">
            <Search size={16} /> Analyse
          </button>
        </form>

        {/* Quick links */}
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="text-xs text-gray-400 self-center">Try:</span>
          {SAMPLE_TAGS.map(t => (
            <button
              key={t}
              onClick={() => { setTagInput(t); setActiveTag(t) }}
              className="text-xs font-mono px-2 py-1 rounded bg-gray-100 text-gray-600
                         hover:bg-navy-800 hover:text-white transition-colors"
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {isLoading && (
        <div className="card p-10 text-center text-gray-400 text-sm">
          Searching…
        </div>
      )}

      {!isLoading && error && (
        <div className="card p-6 text-center text-red-500 text-sm">
          Tag not found or error fetching data.
        </div>
      )}

      {!isLoading && impact && (
        <div className="space-y-5">
          {/* Tag card */}
          <div className="card p-5">
            <div className="flex items-start justify-between flex-wrap gap-3">
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-lg ${tag?.status === 'Active' ? 'bg-green-50' : 'bg-amber-50'}`}>
                  <Tag size={22} className={tag?.status === 'Active' ? 'text-green-700' : 'text-amber-700'} />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xl font-bold text-navy-800">
                      {tag?.tag_number || activeTag}
                    </span>
                    {tag ? (
                      <span className={`text-xs px-2 py-0.5 rounded-full font-semibold
                        ${tag.status === 'Active' ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                        {tag.status === 'Active'
                          ? <span className="flex items-center gap-1"><CheckCircle size={11} /> Active</span>
                          : <span className="flex items-center gap-1"><XCircle size={11} /> Void</span>
                        }
                      </span>
                    ) : (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-semibold">
                        Not in CTDB
                      </span>
                    )}
                  </div>
                  {tag && (
                    <>
                      <p className="text-gray-700 mt-1">{tag.tag_description}</p>
                      <p className="text-sm text-gray-500 mt-0.5">
                        Discipline: <span className="font-medium">{tag.discipline}</span>
                        {tag.voided_at && (
                          <> · Voided: <span className="font-medium text-amber-600">{formatDateShort(tag.voided_at)}</span></>
                        )}
                      </p>
                    </>
                  )}
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-gray-900">{docs.length}</div>
                <div className="text-xs text-gray-500">document{docs.length !== 1 ? 's' : ''} referencing this tag</div>
              </div>
            </div>
          </div>

          {/* Void impact warning */}
          {hasVoidIssue && (
            <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 flex items-start gap-3">
              <AlertTriangle size={20} className="text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-amber-800">Change Management Alert</p>
                <p className="text-sm text-amber-700 mt-0.5">
                  Tag <span className="font-mono font-bold">{tag.tag_number}</span> is <strong>Void</strong> but still
                  referenced in <strong>{docs.length}</strong> document{docs.length !== 1 ? 's' : ''}.
                  These documents require revision before re-issue.
                </p>
              </div>
            </div>
          )}

          {/* Documents list */}
          <div className="card">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
              <Link2 size={18} className="text-navy-800" />
              <h2 className="font-semibold text-gray-900">Referencing Documents</h2>
            </div>
            {docs.length === 0 ? (
              <div className="py-10 text-center text-gray-400 text-sm">
                No documents reference this tag yet.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50">
                      {['Document No.', 'Title', 'Revision', 'Verified On', 'Tag Status at Verification'].map(h => (
                        <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {docs.map((d, i) => {
                      const sc = STATUS_CONFIG[d.verification_status] || STATUS_CONFIG.not_found
                      return (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-mono font-semibold text-navy-800">
                            {d.document_number}
                          </td>
                          <td className="px-4 py-3 text-gray-700 max-w-xs truncate">
                            {d.document_title || '—'}
                          </td>
                          <td className="px-4 py-3 text-gray-500">{d.document_revision || '—'}</td>
                          <td className="px-4 py-3 text-gray-400 text-xs">
                            {formatDateShort(d.found_at)}
                          </td>
                          <td className="px-4 py-3">
                            <span className={sc.badge}>
                              {sc.icon} {sc.label}
                            </span>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {!activeTag && !isLoading && (
        <div className="card p-12 text-center">
          <div className="flex flex-col items-center gap-4 text-gray-400">
            <FileText size={48} className="text-gray-200" />
            <div>
              <p className="font-medium text-gray-500">Enter a tag number above to start</p>
              <p className="text-sm mt-1">
                See all documents that reference the tag and assess change impact
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
