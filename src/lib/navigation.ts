import {
  LayoutDashboard,
  FileText,
  Search,
  Calendar,
  Mail,
  BookOpen,
  FlaskConical,
  BarChart3,
  Activity,
  DollarSign,
} from 'lucide-react'

export const navigationItems = [
  { label: 'Home', href: '/', icon: LayoutDashboard },
  { label: 'Content Hub', href: '/content-hub', icon: FileText },
  { type: 'separator' as const, label: 'PRODUZIONE' },
  { label: 'Ricerca', href: '/ricerca', icon: Search },
  { label: 'Calendario', href: '/calendario', icon: Calendar },
  { label: 'Newsletter', href: '/newsletter', icon: Mail },
  { label: 'Blog', href: '/blog', icon: BookOpen },
  { type: 'separator' as const, label: 'QUALITA' },
  { label: 'Writing Lab', href: '/writing-lab', icon: FlaskConical },
  { label: 'Metriche', href: '/metriche', icon: BarChart3 },
  { type: 'separator' as const, label: 'SISTEMA' },
  { label: 'Pipeline Health', href: '/revenue', icon: Activity },
  { label: 'Costi API', href: '/costi-api', icon: DollarSign },
] as const
