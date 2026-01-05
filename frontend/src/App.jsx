import { Routes, Route } from 'react-router-dom'
import { Container, AppBar, Toolbar, Typography, Box, Tabs, Tab } from '@mui/material'
import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

import OnlineEvaluation from './pages/OnlineEvaluation'
import BatchEvaluation from './pages/BatchEvaluation'
import PerformanceEvaluation from './pages/PerformanceEvaluation'

function App() {
  const navigate = useNavigate()
  const location = useLocation()

  const getTabValue = () => {
    if (location.pathname.startsWith('/batch')) return 1
    if (location.pathname.startsWith('/performance')) return 2
    return 0
  }

  const handleTabChange = (event, newValue) => {
    const paths = ['/', '/batch', '/performance']
    navigate(paths[newValue])
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            LLM Evaluation Toolkit
          </Typography>
        </Toolbar>
        <Tabs
          value={getTabValue()}
          onChange={handleTabChange}
          textColor="inherit"
          indicatorColor="secondary"
          sx={{ backgroundColor: 'primary.dark' }}
        >
          <Tab label="Online Evaluation" />
          <Tab label="Batch Evaluation" />
          <Tab label="Performance Evaluation" />
        </Tabs>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
        <Routes>
          <Route path="/" element={<OnlineEvaluation />} />
          <Route path="/batch" element={<BatchEvaluation />} />
          <Route path="/performance" element={<PerformanceEvaluation />} />
        </Routes>
      </Container>

      <Box
        component="footer"
        sx={{
          py: 2,
          px: 2,
          mt: 'auto',
          backgroundColor: (theme) => theme.palette.grey[200],
        }}
      >
        <Container maxWidth="xl">
          <Typography variant="body2" color="text.secondary" align="center">
            LLM Evaluation Toolkit - Google Gemini Model Testing
          </Typography>
        </Container>
      </Box>
    </Box>
  )
}

export default App
