interface Props {
  title: string
  children: React.ReactNode
}

export default function Section({ title, children }: Props) {
  return (
    <section className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/70">
        <h3 className="font-semibold text-gray-800 text-sm uppercase tracking-wide">{title}</h3>
      </div>
      <div className="px-6 py-5">{children}</div>
    </section>
  )
}
