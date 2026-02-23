import { useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { CheckCircle, AlertTriangle, XCircle, Info, ChevronDown, ChevronUp } from 'lucide-react'
import { STATUS_CONFIG, formatDate } from '../utils/helpers'

const STATUS_ORDER = ['valid_active', 'valid_void', 'not_found', 'shorthand_detected']
const PIE_COLORS = {
  valid_active: '#16a34a',
  valid_void:   '#d97706',
  not_found:    '#dc2626',
  shorthand_detected: '#2563eb',
}

function SummaryBadge({ count, label, icon, color, bg }) {
  return (
    <div className={`${bg} rounded-lg p-4 flex items-center gap-3`}>
      <span className="text-2xl">{icon}</span>
      <div>
        <div className={`text-2xl font-bold ${color}`}>{count}</div>
        <div className={`text-xs font-medium ${color} opacity-80`}>{label}</div>
      </div>
    </div>
  )
}

function TagRow({ tag }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = STATUS_CONFIG[tag.verification_status] || STATUS_CONFIG.not_found

  return (
    <>
      <tr
        className={`border-b border-gray-50 hover:bg-gray-50 transition-colors ${cfg.bg}`}
        onClick={() => tag.is_shorthand && setExpanded(!expanded)}
        style={{ cursor: tag.is_shorthand ? 'pointer' : 'default' }}
      >
        <td className="px-4 py-3 font-mono text-sm font-semibold text-gray-900">
          <div className="flex items-center gap-2">
            {tag.tag_number}
            {tag.is_shorthand && (
              <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded font-normal">
                expanded
              </span>
            )}
          </div>
          {tag.is_shorthand && (
            <div className="text-xs text-gray-400 font-normal">from: {tag.original_shorthand}</div>
          )}
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 max-w-xs">
          {tag.ctdb_description || <span className="text-gray-300 italic">—</span>}
        </td>
        <td className="px-4 py-3 text-sm text-gray-500">
          {tag.ctdb_discipline || '—'}
        </td>
        <td className="px-4 py-3">
          <span className={cfg.badge}>
            {cfg.icon} {cfg.label}
          </span>
        </td>
        <td className="px-4 py-3 text-sm text-gray-400">
          {tag.page_number ? `p.${tag.page_number}` : '—'}
        </td>
        <td className="px-4 py-3 text-xs text-gray-400 font-mono max-w-xs truncate">
          {tag.raw_text !== tag.tag_number ? tag.raw_text : '—'}
        </td>
      </tr>
    </>
  )
}

export default function VerificationReport({ report }) {
  const { document: doc, summary, tags = [], extraction_method, page_count } = report
  const [filter, setFilter] = useState('all')
  const [sortKey, setSortKey] = useState('tag_number')
  const [sortAsc, setSortAsc] = useState(true)

  if (!summary || !doc) {
    return <div className="card p-8 text-center text-gray-400">No report data.</div>
  }

  const isPass = summary.overall_status === 'pass'

  const pieData = STATUS_ORDER
    .map(s => ({
      name: STATUS_CONFIG[s]?.label || s,
      value: summary[s] || 0,
      key: s,
    }))
    .filter(d => d.value > 0)

  const filteredTags = tags
    .filter(t => filter === 'all' || t.verification_status === filter)
    .sort((a, b) => {
      const va = a[sortKey] || ''
      const vb = b[sortKey] || ''
      return sortAsc
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va))
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
    <div className="space-y-5">
      {/* Document info + overall status */}
      <div className="card p-5">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-lg font-bold text-navy-800">{doc.document_number}</span>
              {doc.document_revision && (
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded font-medium">
                  Rev {doc.document_revision}
                </span>
              )}
            </div>
            {doc.document_title && (
              <p className="text-gray-600 text-sm">{doc.document_title}</p>
            )}
            <p className="text-xs text-gray-400 mt-1">
              {doc.filename} · {page_count} page{page_count !== 1 ? 's' : ''} · extracted via {extraction_method}
            </p>
          </div>
          <div className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-sm
            ${isPass ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-700'}`}>
            {isPass
              ? <><CheckCircle size={18} /> PASS — All Tags Valid</>
              : <><AlertTriangle size={18} /> ISSUES FOUND</>
            }
          </div>
        </div>
      </div>

      {/* Summary cards + pie chart */}
      <div className="grid lg:grid-cols-3 gap-5">
        <div className="card p-5 lg:col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <SummaryBadge
            count={summary.total}
            label="Total Tags"
            icon="🏷️"
            color="text-gray-700"
            bg="bg-gray-50"
          />
          <SummaryBadge
            count={summary.valid_active}
            label="Valid & Active"
            icon="✅"
            color="text-green-700"
            bg="bg-green-50"
          />
          <SummaryBadge
            count={summary.valid_void}
            label="Valid but Void"
            icon="⚠️"
            color="text-amber-700"
            bg="bg-amber-50"
          />
          <SummaryBadge
            count={summary.not_found}
            label="Not in CTDB"
            icon="❌"
            color="text-red-700"
            bg="bg-red-50"
          />
          {summary.shorthand_detected > 0 && (
            <div className="col-span-2 sm:col-span-4">
              <SummaryBadge
                count={summary.shorthand_detected}
                label="Shorthand Detected"
                icon="🔵"
                color="text-blue-700"
                bg="bg-blue-50"
              />
            </div>
          )}
        </div>

        {pieData.length > 0 && (
          <div className="card p-5">
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={70}
                  dataKey="value"
                  paddingAngle={3}
                >
                  {pieData.map((entry) => (
                    <Cell key={entry.key} fill={PIE_COLORS[entry.key]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Tag table */}
      <div className="card">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-wrap gap-3">
          <h2 className="font-semibold text-gray-900">Tag Details ({filteredTags.length})</h2>
          <div className="flex items-center gap-2 flex-wrap">
            {['all', ...STATUS_ORDER].map(s => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`text-xs px-3 py-1.5 rounded-full font-medium border transition-colors
                  ${filter === s
                    ? 'bg-navy-800 text-white border-navy-800'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
                  }`}
              >
                {s === 'all' ? 'All' : STATUS_CONFIG[s]?.label}
                {s !== 'all' && summary[s] > 0 && (
                  <span className="ml-1.5 text-xs opacity-70">({summary[s]})</span>
                )}
              </button>
            ))}
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {[
                  { key: 'tag_number', label: 'Tag Number' },
                  { key: 'ctdb_description', label: 'Description' },
                  { key: 'ctdb_discipline', label: 'Discipline' },
                  { key: 'verification_status', label: 'Status' },
                  { key: 'page_number', label: 'Page' },
                  { key: 'raw_text', label: 'Raw Text' },
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
            <tbody>
              {filteredTags.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-gray-400 text-sm">
                    No tags found for this filter.
                  </td>
                </tr>
              ) : (
                filteredTags.map((t, i) => <TagRow key={`${t.tag_number}-${i}`} tag={t} />)
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
