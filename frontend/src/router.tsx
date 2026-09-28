import { createBrowserRouter, type RouteObject } from 'react-router'

import { Layout, NotFound } from './components/Layout'
import { DocumentPage } from './pages/DocumentPage'
import { DocumentsPage } from './pages/DocumentsPage'
import { SessionPage } from './pages/SessionPage'

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: '/', element: <DocumentsPage /> },
      { path: '/documents/:documentId', element: <DocumentPage /> },
      { path: '/sessions/:sessionId', element: <SessionPage /> },
      { path: '*', element: <NotFound /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
