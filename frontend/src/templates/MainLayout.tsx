interface Props {
  sidebar: React.ReactNode
  children: React.ReactNode
}

export default function MainLayout({ sidebar, children }: Props) {
  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {sidebar}
      <main className="flex-1 min-w-0 overflow-hidden flex flex-col">{children}</main>
    </div>
  )
}
