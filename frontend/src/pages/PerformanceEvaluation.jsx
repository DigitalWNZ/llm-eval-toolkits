import { useState } from 'react'
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Grid,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Chip,
  Checkbox,
  FormControlLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import { Download as DownloadIcon } from '@mui/icons-material'
import { performanceEvaluation } from '../services/api'

const GEMINI_MODELS = [
  'gemini-2.5-pro',
  'gemini-2.5-flash',
  'gemini-2.5-flash-lite',
  'gemini-3-pro-preview',
  'gemini-3-flash-preview',
  'gemini-3.0-flash-lite',
]

const REQUEST_SIZES = [1000, 2000, 5000, 10000, 50000, 100000]
const THINKING_LEVELS = ['minimum', 'low', 'medium', 'high']

function PerformanceEvaluation() {
  const [selectedModels, setSelectedModels] = useState(['gemini-2.5-flash'])
  const [selectedSizes, setSelectedSizes] = useState([1000])
  const [selectedLevels, setSelectedLevels] = useState([])
  const [thinkingBudgets, setThinkingBudgets] = useState('')
  const [iterations, setIterations] = useState(1)
  const [cacheEnabled, setCacheEnabled] = useState(false)
  const [project, setProject] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [results, setResults] = useState(null)

  const hasGemini3 = selectedModels.some((m) => m.includes('3.0') || m.includes('3-0'))

  const handleSubmit = async () => {
    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      // Validate Gemini 3.0 constraints
      if (hasGemini3 && selectedLevels.length > 0 && thinkingBudgets.trim()) {
        setError('Gemini 3.0 models cannot use both thinking levels and budgets')
        setLoading(false)
        return
      }

      // Parse thinking budgets
      let budgets = null
      if (thinkingBudgets.trim()) {
        budgets = thinkingBudgets.split(',').map((b) => parseInt(b.trim()))
      }

      const data = {
        models: selectedModels,
        request_sizes: selectedSizes,
        thinking_levels: selectedLevels.length > 0 ? selectedLevels : null,
        thinking_budgets: budgets,
        iterations: iterations,
        cache_enabled: cacheEnabled,
        project: project,
      }

      const result = await performanceEvaluation.benchmark(data)
      setResults(result)
      setSuccess(result.message)
    } catch (err) {
      setError('Error: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadCSV = (filePath, fileType) => {
    const filename = filePath.split('/').pop()
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const downloadUrl = `${baseUrl}/api/performance/download/${fileType}/${filename}`
    window.location.href = downloadUrl
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Performance Evaluation
      </Typography>

      <Grid container spacing={3}>
        {/* Configuration Panel - Full Width */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Benchmark Configuration
            </Typography>

            <Grid container spacing={2}>
              {/* Model Selection */}
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Models</InputLabel>
                  <Select
                    multiple
                    value={selectedModels}
                    onChange={(e) => setSelectedModels(e.target.value)}
                    input={<OutlinedInput label="Models" />}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {GEMINI_MODELS.map((model) => (
                      <MenuItem key={model} value={model}>
                        <Checkbox checked={selectedModels.indexOf(model) > -1} />
                        {model}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {/* Request Sizes */}
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Request Sizes (tokens)</InputLabel>
                  <Select
                    multiple
                    value={selectedSizes}
                    onChange={(e) => setSelectedSizes(e.target.value)}
                    input={<OutlinedInput label="Request Sizes (tokens)" />}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip key={value} label={`${value / 1000}K`} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {REQUEST_SIZES.map((size) => (
                      <MenuItem key={size} value={size}>
                        <Checkbox checked={selectedSizes.indexOf(size) > -1} />
                        {size / 1000}K tokens
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {/* Thinking Levels */}
              <Grid item xs={12} sm={6} md={3}>
                <FormControl fullWidth>
                  <InputLabel>Thinking Levels</InputLabel>
                  <Select
                    multiple
                    value={selectedLevels}
                    onChange={(e) => setSelectedLevels(e.target.value)}
                    input={<OutlinedInput label="Thinking Levels" />}
                    disabled={hasGemini3 && thinkingBudgets.trim()}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {THINKING_LEVELS.map((level) => (
                      <MenuItem key={level} value={level}>
                        <Checkbox checked={selectedLevels.indexOf(level) > -1} />
                        {level}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {/* Thinking Budgets */}
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  label="Thinking Budgets"
                  fullWidth
                  value={thinkingBudgets}
                  onChange={(e) => setThinkingBudgets(e.target.value)}
                  disabled={hasGemini3 && selectedLevels.length > 0}
                  helperText="e.g., 512, 1000, 5000"
                />
              </Grid>

              {/* Iterations */}
              <Grid item xs={12} sm={6} md={2}>
                <TextField
                  label="Iterations"
                  type="number"
                  fullWidth
                  value={iterations}
                  onChange={(e) => {
                    const val = e.target.value
                    setIterations(val === '' ? '' : parseInt(val) || 1)
                  }}
                  onBlur={(e) => {
                    if (e.target.value === '' || parseInt(e.target.value) < 1) {
                      setIterations(1)
                    }
                  }}
                  InputProps={{ inputProps: { min: 1 } }}
                />
              </Grid>

              {/* Project */}
              <Grid item xs={12} sm={6} md={3}>
                <TextField
                  label="GCP Project ID"
                  fullWidth
                  required
                  value={project}
                  onChange={(e) => setProject(e.target.value)}
                />
              </Grid>

              {/* Cache */}
              <Grid item xs={12} sm={6} md={2}>
                <FormControlLabel
                  control={<Checkbox checked={cacheEnabled} onChange={(e) => setCacheEnabled(e.target.checked)} />}
                  label="Enable Caching"
                  sx={{ mt: 1 }}
                />
              </Grid>

              {/* Submit Button */}
              <Grid item xs={12} md={5}>
                <Button
                  variant="contained"
                  fullWidth
                  size="large"
                  onClick={handleSubmit}
                  disabled={loading || !project || selectedModels.length === 0 || selectedSizes.length === 0}
                >
                  {loading ? <CircularProgress size={24} /> : 'Run Benchmark'}
                </Button>
              </Grid>

              {hasGemini3 && (
                <Grid item xs={12}>
                  <Alert severity="warning">
                    Gemini 3.0 models: thinking levels and budgets are mutually exclusive
                  </Alert>
                </Grid>
              )}

              {error && (
                <Grid item xs={12}>
                  <Alert severity="error">{error}</Alert>
                </Grid>
              )}

              {success && (
                <Grid item xs={12}>
                  <Alert severity="success">{success}</Alert>
                </Grid>
              )}
            </Grid>
          </Paper>
        </Grid>

        {/* Results Panel - Full Width */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Results</Typography>
              {results && (
                <Box>
                  <Button
                    size="small"
                    startIcon={<DownloadIcon />}
                    onClick={() => handleDownloadCSV(results.raw_csv_path, 'raw')}
                    sx={{ mr: 1 }}
                  >
                    Raw CSV
                  </Button>
                  <Button
                    size="small"
                    startIcon={<DownloadIcon />}
                    onClick={() => handleDownloadCSV(results.analysis_csv_path, 'analysis')}
                  >
                    Analysis CSV
                  </Button>
                </Box>
              )}
            </Box>

            {results ? (
              <TableContainer sx={{ maxHeight: '600px', overflowX: 'auto' }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ minWidth: 150 }}>Model</TableCell>
                      <TableCell sx={{ minWidth: 80 }}>Size</TableCell>
                      <TableCell sx={{ minWidth: 80 }}>Level</TableCell>
                      <TableCell sx={{ minWidth: 80 }}>Budget</TableCell>
                      <TableCell sx={{ minWidth: 70 }}>Cache</TableCell>
                      <TableCell sx={{ minWidth: 100 }}>Median (ms)</TableCell>
                      <TableCell sx={{ minWidth: 100 }}>P90 (ms)</TableCell>
                      <TableCell sx={{ minWidth: 100 }}>P99 (ms)</TableCell>
                      <TableCell sx={{ minWidth: 110 }}>Input Tokens</TableCell>
                      <TableCell sx={{ minWidth: 120 }}>Cached Tokens</TableCell>
                      <TableCell sx={{ minWidth: 120 }}>Output Tokens</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {results.statistics.map((stat, index) => (
                      <TableRow key={index} hover>
                        <TableCell>{stat.model}</TableCell>
                        <TableCell>{stat.request_size / 1000}K</TableCell>
                        <TableCell>{stat.thinking_level || '-'}</TableCell>
                        <TableCell>{stat.thinking_budget || '-'}</TableCell>
                        <TableCell>{stat.cache_enabled ? 'Yes' : 'No'}</TableCell>
                        <TableCell>{stat.median_ttft_ms.toFixed(2)}</TableCell>
                        <TableCell>{stat.p90_ttft_ms.toFixed(2)}</TableCell>
                        <TableCell>{stat.p99_ttft_ms.toFixed(2)}</TableCell>
                        <TableCell>{Math.round(stat.avg_input_tokens).toLocaleString()}</TableCell>
                        <TableCell>{Math.round(stat.avg_cached_tokens).toLocaleString()}</TableCell>
                        <TableCell>{Math.round(stat.avg_output_tokens).toLocaleString()}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography color="text.secondary">No results yet. Configure and run a benchmark to see results.</Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default PerformanceEvaluation
