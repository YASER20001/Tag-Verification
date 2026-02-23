export const STATUS_CONFIG = {
  valid_active: {
    label: 'Valid (Active)',
    color: 'text-green-700',
    bg: 'bg-green-50',
    border: 'border-green-200',
    badge: 'badge-valid',
    icon: '✅',
    dot: 'bg-green-500',
  },
  valid_void: {
    label: 'Valid (Void)',
    color: 'text-amber-700',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    badge: 'badge-void',
    icon: '⚠️',
    dot: 'bg-amber-500',
  },
  not_found: {
    label: 'Not Found',
    color: 'text-red-700',
    bg: 'bg-red-50',
    border: 'border-red-200',
    badge: 'badge-notfound',
    icon: '❌',
    dot: 'bg-red-500',
  },
  shorthand_detected: {
    label: 'Shorthand',
    color: 'text-blue-700',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    badge: 'badge-shorthand',
    icon: '🔵',
    dot: 'bg-blue-500',
  },
}

export const DOC_STATUS_CONFIG = {
  pass: { label: 'Pass', color: 'text-green-700', bg: 'bg-green-100', icon: '✅' },
  issues: { label: 'Issues Found', color: 'text-red-700', bg: 'bg-red-100', icon: '❌' },
  approved: { label: 'Approved', color: 'text-blue-700', bg: 'bg-blue-100', icon: '✔️' },
  pending: { label: 'Pending', color: 'text-gray-500', bg: 'bg-gray-100', icon: '⏳' },
}

export function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export function formatDateShort(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}
