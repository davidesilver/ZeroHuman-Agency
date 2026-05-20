import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'ZeroHuman — Content Engine',
    short_name: 'ZeroHuman',
    description: 'Autonomous AI content operations — research, draft, review, publish across every brand.',
    start_url: '/',
    display: 'standalone',
    background_color: '#0D0D0D',
    theme_color: '#FF6B4A',
    icons: [
      {
        src: '/brand/zerohuman-mark-64.png',
        sizes: '64x64',
        type: 'image/png',
      },
      {
        src: '/brand/zerohuman-mark-512.png',
        sizes: '512x512',
        type: 'image/png',
      },
      {
        src: '/brand/zerohuman-mark-1024.png',
        sizes: '1024x1024',
        type: 'image/png',
      },
    ],
  }
}
