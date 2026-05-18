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
  Share2,
  Building,
  Settings,
  Brain,
  Rocket,
} from 'lucide-react'

/**
 * Navigation structure — YouTube Studio grouping pattern.
 *
 * Groups:
 *  - OVERVIEW: high-level dashboard
 *  - CONTENT: production surfaces
 *  - INTELLIGENCE: research & quality
 *  - ANALYTICS: metrics & costs
 *  - SYSTEM: configuration
 *
 * Each separator becomes an eyebrow label in the sidebar.
 */
export const navigationItems = [
  { type: 'separator' as const, label: 'Overview' },
  { label: 'Dashboard', href: '/', icon: LayoutDashboard },

  { type: 'separator' as const, label: 'Content' },
  { label: 'Content Hub', href: '/content-hub', icon: FileText },
  { label: 'Calendar', href: '/calendario', icon: Calendar },
  { label: 'Newsletter', href: '/newsletter', icon: Mail },
  { label: 'Blog', href: '/blog', icon: BookOpen },
  { label: 'Social', href: '/social', icon: Share2 },

  { type: 'separator' as const, label: 'Intelligence' },
  { label: 'Research', href: '/ricerca', icon: Search },
  { label: 'Writing Lab', href: '/writing-lab', icon: FlaskConical },
  { label: 'Memory', href: '/memory', icon: Brain },

  { type: 'separator' as const, label: 'Analytics' },
  { label: 'Metrics', href: '/metriche', icon: BarChart3 },
  { label: 'Revenue', href: '/revenue', icon: Activity },
  { label: 'API Costs', href: '/costi-api', icon: DollarSign },

  { type: 'separator' as const, label: 'System' },
  { label: 'Brands', href: '/brands', icon: Building },
  { label: 'Settings', href: '/settings', icon: Settings },
  { label: 'Setup', href: '/setup', icon: Rocket },
] as const
