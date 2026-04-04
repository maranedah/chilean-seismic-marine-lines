interface Props {
  label: string
  value: string | number
  subtitle?: string
  colorClass?: string
}

export default function MetricCard({
  label,
  value,
  subtitle,
  colorClass = 'text-blue-600',
}: Props) {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
      <p className="text-sm font-medium text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${colorClass}`}>{value}</p>
      {subtitle && <p className="text-xs text-gray-400 mt-1">{subtitle}</p>}
    </div>
  )
}
