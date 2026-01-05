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
  Link,
} from '@mui/material'
import { Download as DownloadIcon } from '@mui/icons-material'
import { performanceEvaluation } from '../services/api'

const GEMINI_MODELS = [
  'gemini-2.5-pro',
  'gemini-2.5-flash',
  'gemini-2.5-flash-lite',
  'gemini-3.0-pro',
  'gemini-3.0-flash',
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
    // Extract filename from path (e.g., "performance_results/raw_metrics_20260105_100415.csv" -> "raw_metrics_20260105_100415.csv")
    const filename = filePath.split('/').pop()

    // Construct download URL
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const downloadUrl = `${baseUrl}/api/performance/download/${fileType}/${filename}`

    // Trigger download
    window.location.href = downloadUrl
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Performance Evaluation
      </Typography>

      <Grid container spacing={3}>
        {/* Left Panel - Configuration */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Benchmark Configuration
            </Typography>

            {/* Model Selection */}
            <FormControl fullWidth sx={{ mb: 2 }}>
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

            {/* Request Sizes */}
            <FormControl fullWidth sx={{ mb: 2 }}>
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

            {/* Thinking Levels */}
            <FormControl fullWidth sx={{ mb: 2 }}>
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

            {/* Thinking Budgets */}
            <TextField
              label="Thinking Budgets (comma-separated)"
              fullWidth
              value={thinkingBudgets}
              onChange={(e) => setThinkingBudgets(e.target.value)}
              disabled={hasGemini3 && selectedLevels.length > 0}
              helperText="Range varies by model: flash(1-24576), pro(128-32768), lite(512-24576). e.g., 512, 1000, 5000"
              sx={{ mb: 2 }}
            />

            {hasGemini3 && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Gemini 3.0 models: thinking levels and budgets are mutually exclusive
              </Alert>
            )}

            {/* Iterations */}
            <TextField
              label="Iterations per Configuration"
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
              sx={{ mb: 2 }}
            />

            {/* Cache */}
            <FormControlLabel
              control={<Checkbox checked={cacheEnabled} onChange={(e) => setCacheEnabled(e.target.checked)} />}
              label="Enable Caching"
              sx={{ mb: 2 }}
            />

            {/* Project */}
            <TextField
              label="GCP Project ID"
              fullWidth
              required
              value={project}
              onChange={(e) => setProject(e.target.value)}
              sx={{ mb: 2 }}
            />

            {/* Submit Button */}
            <Button
              variant="contained"
              fullWidth
              size="large"
              onClick={handleSubmit}
              disabled={loading || !project || selectedModels.length === 0 || selectedSizes.length === 0}
            >
              {loading ? <CircularProgress size={24} /> : 'Run Benchmark'}
            </Button>

            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}

            {success && (
              <Alert severity="success" sx={{ mt: 2 }}>
                {success}
              </Alert>
            )}
          </Paper>
        </Grid>

        {/* Right Panel - Results */}
        <Grid item xs={12} md={6}>
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
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Model</TableCell>
                      <TableCell>Size</TableCell>
                      <TableCell>Level</TableCell>
                      <TableCell>Budget</TableCell>
                      <TableCell>Cache</TableCell>
                      <TableCell>Median (ms)</TableCell>
                      <TableCell>P90 (ms)</TableCell>
                      <TableCell>P99 (ms)</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {results.statistics.map((stat, index) => (
                      <TableRow key={index}>
                        <TableCell>{stat.model}</TableCell>
                        <TableCell>{stat.request_size / 1000}K</TableCell>
                        <TableCell>{stat.thinking_level || '-'}</TableCell>
                        <TableCell>{stat.thinking_budget || '-'}</TableCell>
                        <TableCell>{stat.cache_enabled ? 'Yes' : 'No'}</TableCell>
                        <TableCell>{stat.median_ttft_ms.toFixed(2)}</TableCell>
                        <TableCell>{stat.p90_ttft_ms.toFixed(2)}</TableCell>
                        <TableCell>{stat.p99_ttft_ms.toFixed(2)}</TableCell>
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
