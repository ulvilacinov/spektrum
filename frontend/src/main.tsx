import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router'

import { createQueryClient, retryUnlessClientError } from './api/queryClient'
import { router } from './router'
import './index.css'

const queryClient = createQueryClient({
  queries: { retry: retryUnlessClientError, refetchOnWindowFocus: false },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)
