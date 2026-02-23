import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import {
  Tag, FileText, CheckCircle, AlertTriangle, Upload, Bell, TrendingUp
} from 'lucide-react'
import { getDashboardStats, getRecentDocs, getAlerts } from '../utils/api'
import { DOC_STATUS_CONFIG, formatDate } from '../utils/helpers'

function StatCard({ title, value, sub, icon: Icon, color = 'text-navy-800', bg = 'bg-blue-50' }) {
  return (
    <div className="card p-5 flex items-start gap-4">
      <div className={`${bg} p-3 rounded-lg`}>
        <Icon size={22} className={color} />
      </div>
      <div>
        <p className="text-sm text-gray-500 font-medium">{title}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5">{value ?? '—'}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { data: stats } = useQuery({ queryKey: ['stats'], queryFn: getDashboardStats })
  const { data: recent } = useQuery({ queryKey: ['recent'], queryFn: getRecentDocs })
  const { data: alerts } = useQuery({ queryKey: ['alerts'], queryFn: getAlerts })

  const chartData = stats ? [
    { name: 'Active Tags', value: stats.active_tags, fill: '#16a34a' },
    { name: 'Void Tags',   value: stats.void_tags,   fill: '#d97706' },
    { name: 'Docs Passed', value: stats.passed_documents, fill: '#2563eb' },
    { name: 'Docs Issues', value: stats.issue_documents,  fill: '#dc2626' },
  ] : []

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">Engineering Tag Verification Overview</p>
        </div>
        <button
          className="btn-primary flex items-center gap-2"
          onClick={() => navigate('/upload')}
        >
          <Upload size={16} />
          Verify Document
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Tags (CTDB)"
          value={stats?.total_tags}
          sub={`${stats?.active_tags ?? 0} active · ${stats?.void_tags ?? 0} void`}
          icon={Tag}
          bg="bg-blue-50"
          color="text-blue-700"
        />
        <StatCard
          title="Documents Verified"
          value={stats?.total_documents}
          icon={FileText}
          bg="bg-slate-100"
          color="text-slate-700"
        />
        <StatCard
          title="Passed Verification"
          value={stats?.passed_documents}
          icon={CheckCircle}
          bg="bg-green-50"
          color="text-green-700"
        />
        <StatCard
          title="Issues Found"
          value={stats?.issue_documents}
          icon={AlertTriangle}
          bg="bg-red-50"
          color="text-red-700"
        />
      </div>

      {/* Chart + Alerts */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Bar chart */}
        <div className="card p-5 lg:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={18} className="text-navy-800" />
            <h2 className="font-semibold text-gray-900">Tag & Document Statistics</h2>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData} barSize={36}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#6b7280' }} />
              <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <rect key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Alerts */}
        <div className="card p-5 flex flex-col">
          <div className="flex items-center gap-2 mb-4">
            <Bell size={18} className="text-amber-600" />
            <h2 className="font-semibold text-gray-900">Void Tag Alerts</h2>
            {alerts?.length > 0 && (
              <span className="ml-auto text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded-full font-bold">
                {alerts.length}
              </span>
            )}
          </div>
          <div className="flex-1 space-y-3 overflow-y-auto max-h-64">
            {!alerts || alerts.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-8">No void tag alerts</p>
            ) : (
              alerts.map((a) => (
                <div
                  key={a.tag_number}
                  className="p-3 rounded-lg bg-amber-50 border border-amber-200 cursor-pointer hover:bg-amber-100 transition-colors"
                  onClick={() => navigate(`/impact?tag=${a.tag_number}`)}
                >
                  <p className="text-sm font-mono font-bold text-amber-900">{a.tag_number}</p>
                  <p className="text-xs text-amber-700 truncate">{a.tag_description}</p>
                  <p className="text-xs text-amber-600 mt-1">
                    {a.affected_documents.length} document{a.affected_documents.length !== 1 ? 's' : ''} affected
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Recent Verifications */}
      <div className="card">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Recent Verifications</h2>
          <button
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            onClick={() => navigate('/upload')}
          >
            + New
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                {['Document No.', 'Title', 'Rev', 'Uploaded', 'Tags', 'Status'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {!recent || recent.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-gray-400 text-sm">
                    No documents verified yet.{' '}
                    <button className="text-blue-600 underline" onClick={() => navigate('/upload')}>
                      Upload one now.
                    </button>
                  </td>
                </tr>
              ) : (
                recent.map((d) => {
                  const sc = DOC_STATUS_CONFIG[d.verification_status] || DOC_STATUS_CONFIG.pending
                  return (
                    <tr
                      key={d.id}
                      className="hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/upload/${d.id}`)}
                    >
                      <td className="px-4 py-3 font-mono font-medium text-navy-800">
                        {d.document_number}
                      </td>
                      <td className="px-4 py-3 text-gray-700 max-w-xs truncate">
                        {d.document_title || '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-500">{d.document_revision || '—'}</td>
                      <td className="px-4 py-3 text-gray-500">{formatDate(d.uploaded_at)}</td>
                      <td className="px-4 py-3">
                        <span className="font-semibold">{d.tags_found}</span>
                        <span className="text-gray-400 text-xs ml-1">
                          ({d.tags_valid}✅ {d.tags_void}⚠️ {d.tags_not_found}❌)
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs font-semibold px-2 py-1 rounded-full ${sc.bg} ${sc.color}`}>
                          {sc.icon} {sc.label}
                        </span>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
