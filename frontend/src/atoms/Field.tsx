interface Props {
  label: string
  value?: string | number | null
}

export default function Field({ label, value }: Props) {
  if (value == null || value === '') return null
  return (
    <div className="flex gap-2 text-sm">
      <span className="font-medium text-gray-500 shrink-0 w-36">{label}</span>
      <span className="text-gray-900">{value}</span>
    </div>
  )
}
