import { createBrowserRouter, type RouteObject } from 'react-router'

import { Layout, NotFound } from './components/Layout'
import { DocumentsPage } from './pages/DocumentsPage'

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: '/', element: <DocumentsPage /> },
      { path: '*', element: <NotFound /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
