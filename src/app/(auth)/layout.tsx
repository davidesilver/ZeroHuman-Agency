export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-secondary flex flex-col items-center justify-center px-4">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-foreground tracking-tight">
          Content Engine
        </h1>
      </div>
      {children}
    </div>
  )
}
