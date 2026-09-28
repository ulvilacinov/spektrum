import { createBrowserRouter, type RouteObject } from 'react-router'

import { Layout, NotFound } from './components/Layout'
import { DocumentPage } from './pages/DocumentPage'
import { DocumentsPage } from './pages/DocumentsPage'
import { QuizPage } from './pages/QuizPage'
import { SessionPage } from './pages/SessionPage'
import { WeakWordsPage } from './pages/WeakWordsPage'

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    children: [
      { path: '/', element: <DocumentsPage /> },
      { path: '/documents/:documentId', element: <DocumentPage /> },
      { path: '/documents/:documentId/weak', element: <WeakWordsPage /> },
      { path: '/sessions/:sessionId', element: <SessionPage /> },
      { path: '/sessions/:sessionId/quiz', element: <QuizPage /> },
      { path: '*', element: <NotFound /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
