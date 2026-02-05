import { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Grid,
  Alert,
  CircularProgress,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Card,
  CardContent,
  IconButton,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material'
import { Delete as DeleteIcon, CloudUpload as UploadIcon, Save as SaveIcon, ExpandMore as ExpandMoreIcon, Visibility as VisibilityIcon } from '@mui/icons-material'
import ReactJson from '@microlink/react-json-view'
import { onlineEvaluation } from '../services/api'

const GEMINI_MODELS = [
  'gemini-2.5-pro',
  'gemini-2.5-flash',
  'gemini-2.5-flash-lite',
  'gemini-3-pro-preview',
  'gemini-3-flash-preview',
  'gemini-3.0-flash-lite',
]

function OnlineEvaluation() {
  const [geminiRequest, setGeminiRequest] = useState('')
  const [systemInstruction, setSystemInstruction] = useState('')
  const [geminiConfig, setGeminiConfig] = useState('')
  const [model, setModel] = useState('gemini-2.5-flash')
  const [customModel, setCustomModel] = useState('')
  const [project, setProject] = useState('')
  const [iterations, setIterations] = useState(1)
  const [multimodalFiles, setMultimodalFiles] = useState([])
  const [uploadedFileData, setUploadedFileData] = useState([])
  const [responses, setResponses] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [showRequestPreview, setShowRequestPreview] = useState(false)
  const [previewRequest, setPreviewRequest] = useState('')
  const [useEditedRequest, setUseEditedRequest] = useState(false)

  // Auto-populate system instruction and config when request changes
  useEffect(() => {
    if (geminiRequest.trim()) {
      try {
        const parsed = JSON.parse(geminiRequest)

        // Handle systemInstruction with nested structure: systemInstruction.parts[0].text
        if (parsed.systemInstruction) {
          let instructionText = null

          // Check if it's a string (simple format)
          if (typeof parsed.systemInstruction === 'string') {
            instructionText = parsed.systemInstruction
          }
          // Check if it has parts array (nested format)
          else if (parsed.systemInstruction.parts &&
                   Array.isArray(parsed.systemInstruction.parts) &&
                   parsed.systemInstruction.parts.length > 0 &&
                   parsed.systemInstruction.parts[0].text) {
            instructionText = parsed.systemInstruction.parts[0].text
          }

          if (instructionText) {
            // Replace \n escape sequences with actual newlines
            setSystemInstruction(instructionText.replace(/\\n/g, '\n'))
          }
        }

        // Handle generationConfig
        if (parsed.generationConfig && typeof parsed.generationConfig === 'object') {
          setGeminiConfig(JSON.stringify(parsed.generationConfig, null, 2))
        }
      } catch (err) {
        // Not valid JSON, ignore
      }
    }
  }, [geminiRequest])

  const handleFileUpload = (event) => {
    const file = event.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          // Try to parse as JSON first
          const content = JSON.parse(e.target.result)
          setGeminiRequest(JSON.stringify(content, null, 2))
          // System instruction will be auto-populated by useEffect
        } catch (err) {
          // Not valid JSON, treat as plain text
          setGeminiRequest(e.target.result)
          setError(null) // Clear any previous errors
        }
      }
      reader.readAsText(file)
    }
  }

  const handleMultimodalUpload = async (event) => {
    const files = Array.from(event.target.files)
    if (files.length + multimodalFiles.length > 10) {
      setError('Maximum 10 files allowed')
      return
    }

    try {
      setLoading(true)
      const result = await onlineEvaluation.uploadMultimodal(files)
      setUploadedFileData([...uploadedFileData, ...result.files])
      setMultimodalFiles([...multimodalFiles, ...files])
      setSuccess('Files uploaded successfully')
    } catch (err) {
      setError('Error uploading files: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const removeMultimodalFile = (index) => {
    setMultimodalFiles(multimodalFiles.filter((_, i) => i !== index))
    setUploadedFileData(uploadedFileData.filter((_, i) => i !== index))
  }

  const buildRequestPreview = () => {
    try {
      // Parse and validate inputs
      let parsedRequest = {}
      if (geminiRequest.trim()) {
        try {
          parsedRequest = JSON.parse(geminiRequest)
          // Remove systemInstruction from the request if it exists
          // We'll use the value from the System Instruction field instead
          if (parsedRequest.systemInstruction) {
            delete parsedRequest.systemInstruction
          }
          // Remove generationConfig if it exists - we'll use the config field instead
          if (parsedRequest.generationConfig) {
            delete parsedRequest.generationConfig
          }
        } catch (jsonError) {
          // Not valid JSON, treat as plain text and wrap in Gemini request format
          parsedRequest = {
            contents: [
              {
                role: "user",
                parts: [
                  {
                    text: geminiRequest.trim()
                  }
                ]
              }
            ]
          }
        }
      }

      // Add system instruction in the proper nested structure
      if (systemInstruction && systemInstruction.trim()) {
        if (typeof parsedRequest === 'object' && !Array.isArray(parsedRequest)) {
          parsedRequest.systemInstruction = {
            parts: [
              {
                text: systemInstruction
              }
            ]
          }
        }
      }

      // Add generation config in the proper Gemini format (camelCase)
      if (geminiConfig.trim()) {
        try {
          const parsedConfig = JSON.parse(geminiConfig)
          if (typeof parsedRequest === 'object' && !Array.isArray(parsedRequest)) {
            // Convert snake_case to camelCase for Gemini API
            const geminiFormattedConfig = {}
            for (const [key, value] of Object.entries(parsedConfig)) {
              // Convert common snake_case keys to camelCase
              const camelKey = key
                .replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
              geminiFormattedConfig[camelKey] = value
            }
            parsedRequest.generationConfig = geminiFormattedConfig
          }
        } catch (configError) {
          // Invalid JSON in config, ignore
        }
      }

      // Show only the raw Gemini request format (not the wrapper)
      setPreviewRequest(JSON.stringify(parsedRequest, null, 2))
      setShowRequestPreview(true)
      setUseEditedRequest(false)
    } catch (err) {
      setError('Error building request preview: ' + err.message)
    }
  }

  const handleSubmit = async () => {
    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      let parsedRequest = {}

      // If user has edited the preview request, use that as the gemini_request
      if (useEditedRequest && previewRequest.trim()) {
        parsedRequest = JSON.parse(previewRequest)
      } else {
        // Parse and validate inputs
        if (geminiRequest.trim()) {
          // Try to parse as JSON first, if it fails treat as plain string
          try {
            parsedRequest = JSON.parse(geminiRequest)
            // Remove systemInstruction from the request if it exists
            // We'll use the value from the System Instruction field instead
            if (parsedRequest.systemInstruction) {
              delete parsedRequest.systemInstruction
            }
            // Remove generationConfig if it exists - we'll use the config field instead
            if (parsedRequest.generationConfig) {
              delete parsedRequest.generationConfig
            }
          } catch (jsonError) {
            // Not valid JSON, treat as plain text and wrap in Gemini request format
            parsedRequest = {
              contents: [
                {
                  role: "user",
                  parts: [
                    {
                      text: geminiRequest.trim()
                    }
                  ]
                }
              ]
            }
          }
        }

        // Add system instruction in the proper nested structure
        if (systemInstruction && systemInstruction.trim()) {
          if (typeof parsedRequest === 'object' && !Array.isArray(parsedRequest)) {
            parsedRequest.systemInstruction = {
              parts: [
                {
                  text: systemInstruction
                }
              ]
            }
          }
        }

        // Add generation config in the proper Gemini format (camelCase)
        if (geminiConfig.trim()) {
          try {
            const parsedConfig = JSON.parse(geminiConfig)
            if (typeof parsedRequest === 'object' && !Array.isArray(parsedRequest)) {
              // Convert snake_case to camelCase for Gemini API
              const geminiFormattedConfig = {}
              for (const [key, value] of Object.entries(parsedConfig)) {
                // Convert common snake_case keys to camelCase
                const camelKey = key
                  .replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
                geminiFormattedConfig[camelKey] = value
              }
              parsedRequest.generationConfig = geminiFormattedConfig
            }
          } catch (configError) {
            // Invalid JSON in config, ignore
          }
        }
      }

      // Extract system instruction for the backend's separate field
      let systemInst = null
      if (parsedRequest.systemInstruction?.parts?.[0]?.text) {
        systemInst = parsedRequest.systemInstruction.parts[0].text
      } else if (typeof parsedRequest.systemInstruction === 'string') {
        systemInst = parsedRequest.systemInstruction
      }

      // Extract generation config for the backend's separate field
      let parsedConfig = null
      if (parsedRequest.generationConfig) {
        // Convert camelCase back to snake_case for backend
        parsedConfig = {}
        for (const [key, value] of Object.entries(parsedRequest.generationConfig)) {
          const snakeKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`)
          parsedConfig[snakeKey] = value
        }
      }

      const finalModel = model === 'custom' ? customModel : model

      const data = {
        gemini_request: parsedRequest,
        system_instruction: systemInst,
        gemini_config: parsedConfig,
        model: finalModel,
        project: project,
        iterations: iterations,
        multimodal_files: uploadedFileData.length > 0 ? uploadedFileData : null,
      }

      const result = await onlineEvaluation.evaluate(data)
      setResponses(result.responses)
      setSuccess(result.message)
    } catch (err) {
      setError('Error: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleSaveResponses = () => {
    const saveData = {
      metadata: {
        timestamp: new Date().toISOString(),
        total_iterations: responses.length,
        models: [...new Set(responses.map((r) => r.model).filter(Boolean))],
      },
      responses: responses,
    }
    const blob = new Blob([JSON.stringify(saveData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `gemini_responses_${new Date().getTime()}.json`
    a.click()
  }

  const calculateTtftStatistics = () => {
    const ttfts = responses
      .map((r) => r.ttft_ms)
      .filter((t) => t !== undefined && t !== null)
      .sort((a, b) => a - b)

    if (ttfts.length === 0) return null

    const getPercentile = (arr, percentile) => {
      const index = Math.ceil((percentile / 100) * arr.length) - 1
      return arr[Math.max(0, index)]
    }

    return {
      p50: getPercentile(ttfts, 50),
      p90: getPercentile(ttfts, 90),
      p95: getPercentile(ttfts, 95),
      p99: getPercentile(ttfts, 99),
      count: ttfts.length,
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Online Evaluation
      </Typography>

      <Grid container spacing={3}>
        {/* Left Panel - Inputs */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Configuration
            </Typography>

            {/* Request Upload */}
            <Button
              variant="outlined"
              component="label"
              fullWidth
              startIcon={<UploadIcon />}
              sx={{ mb: 2 }}
            >
              Upload Gemini Request File
              <input type="file" hidden accept=".json" onChange={handleFileUpload} />
            </Button>

            {/* Gemini Request */}
            <TextField
              label="Gemini Request (JSON or Text)"
              multiline
              rows={8}
              fullWidth
              value={geminiRequest}
              onChange={(e) => setGeminiRequest(e.target.value)}
              sx={{ mb: 2 }}
              helperText="Enter plain text or paste Gemini API request JSON"
            />

            {/* Multimodal Files Upload */}
            <Typography variant="subtitle2" gutterBottom>
              Multimodal Files (Optional)
            </Typography>
            <Button
              variant="outlined"
              component="label"
              fullWidth
              startIcon={<UploadIcon />}
              sx={{ mb: 1 }}
            >
              Upload Multimodal Files (Max 10)
              <input
                type="file"
                hidden
                multiple
                accept="image/*,video/*,audio/*,.pdf"
                onChange={handleMultimodalUpload}
              />
            </Button>

            {/* Uploaded Files Display */}
            {multimodalFiles.length > 0 && (
              <Box sx={{ mb: 2 }}>
                {multimodalFiles.map((file, index) => (
                  <Chip
                    key={index}
                    label={file.name}
                    onDelete={() => removeMultimodalFile(index)}
                    sx={{ mr: 1, mb: 1 }}
                  />
                ))}
              </Box>
            )}

            {/* System Instruction */}
            <TextField
              label="System Instruction"
              multiline
              rows={4}
              fullWidth
              value={systemInstruction}
              onChange={(e) => setSystemInstruction(e.target.value)}
              sx={{ mb: 2 }}
              helperText="Newlines will be automatically escaped"
            />

            {/* Gemini Configuration */}
            <TextField
              label="Gemini Configuration (JSON)"
              multiline
              rows={4}
              fullWidth
              value={geminiConfig}
              onChange={(e) => setGeminiConfig(e.target.value)}
              sx={{ mb: 2 }}
              helperText='e.g., {"temperature": 0.7, "topK": 40} or {"temperature": 0.7, "top_k": 40}'
            />

            {/* Model Selection */}
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Model</InputLabel>
              <Select value={model} onChange={(e) => setModel(e.target.value)} label="Model">
                {GEMINI_MODELS.map((m) => (
                  <MenuItem key={m} value={m}>
                    {m}
                  </MenuItem>
                ))}
                <MenuItem value="custom">Custom...</MenuItem>
              </Select>
            </FormControl>

            {model === 'custom' && (
              <TextField
                label="Custom Model Name"
                fullWidth
                value={customModel}
                onChange={(e) => setCustomModel(e.target.value)}
                sx={{ mb: 2 }}
              />
            )}

            {/* Project */}
            <TextField
              label="GCP Project ID"
              fullWidth
              required
              value={project}
              onChange={(e) => setProject(e.target.value)}
              sx={{ mb: 2 }}
            />

            {/* Iterations */}
            <TextField
              label="Number of Iterations"
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

            {/* Submit Button */}
            <Button
              variant="contained"
              fullWidth
              size="large"
              onClick={handleSubmit}
              disabled={loading || !project}
              sx={{ mb: 2 }}
            >
              {loading ? <CircularProgress size={24} /> : 'Submit'}
            </Button>

            {/* Show Request Button */}
            <Button
              variant="outlined"
              fullWidth
              size="large"
              onClick={buildRequestPreview}
              startIcon={<VisibilityIcon />}
            >
              Show Request
            </Button>

            {/* Request Preview Accordion */}
            {showRequestPreview && (
              <Accordion expanded={showRequestPreview} sx={{ mt: 2 }}>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  onClick={() => setShowRequestPreview(!showRequestPreview)}
                >
                  <Typography variant="subtitle1">Request Preview (Editable)</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                      Raw Gemini API request format (matching your input). Click on values to edit.
                    </Typography>
                    <ReactJson
                      src={JSON.parse(previewRequest)}
                      name={null}
                      collapsed={2}
                      enableClipboard={true}
                      displayDataTypes={false}
                      onEdit={(edit) => {
                        setPreviewRequest(JSON.stringify(edit.updated_src, null, 2))
                        setUseEditedRequest(true)
                      }}
                      onAdd={(add) => {
                        setPreviewRequest(JSON.stringify(add.updated_src, null, 2))
                        setUseEditedRequest(true)
                      }}
                      onDelete={(del) => {
                        setPreviewRequest(JSON.stringify(del.updated_src, null, 2))
                        setUseEditedRequest(true)
                      }}
                    />
                  </Box>
                </AccordionDetails>
              </Accordion>
            )}
          </Paper>
        </Grid>

        {/* Right Panel - Responses */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">Responses</Typography>
              {responses.length > 0 && (
                <Button startIcon={<SaveIcon />} onClick={handleSaveResponses}>
                  Save
                </Button>
              )}
            </Box>

            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            {success && (
              <Alert severity="success" sx={{ mb: 2 }}>
                {success}
              </Alert>
            )}

            {/* TTFT Statistics */}
            {(() => {
              const stats = calculateTtftStatistics()
              return stats && stats.count >= 2 ? (
                <Card sx={{ mb: 3, bgcolor: 'primary.light', color: 'primary.contrastText' }}>
                  <CardContent>
                    <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
                      TTFT Statistics ({stats.count} iterations)
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={6} sm={3}>
                        <Box>
                          <Typography variant="caption" sx={{ opacity: 0.8 }}>
                            P50 (Median)
                          </Typography>
                          <Typography variant="h6">{stats.p50.toFixed(2)} ms</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Box>
                          <Typography variant="caption" sx={{ opacity: 0.8 }}>
                            P90
                          </Typography>
                          <Typography variant="h6">{stats.p90.toFixed(2)} ms</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Box>
                          <Typography variant="caption" sx={{ opacity: 0.8 }}>
                            P95
                          </Typography>
                          <Typography variant="h6">{stats.p95.toFixed(2)} ms</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Box>
                          <Typography variant="caption" sx={{ opacity: 0.8 }}>
                            P99
                          </Typography>
                          <Typography variant="h6">{stats.p99.toFixed(2)} ms</Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              ) : null
            })()}

            {responses.length > 0 ? (
              <Box>
                {responses.map((response, index) => {
                  // Extract TTFT and create response copy without it
                  const ttft = response.ttft_ms
                  const { ttft_ms, ...responseWithoutTtft } = response

                  return (
                    <Card key={index} sx={{ mb: 2 }}>
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                          <Typography variant="subtitle2">
                            Response {index + 1}
                          </Typography>
                          {ttft !== undefined && (
                            <Chip
                              label={`TTFT: ${ttft.toFixed(2)} ms`}
                              color="primary"
                              size="small"
                            />
                          )}
                        </Box>
                        <ReactJson
                          src={responseWithoutTtft}
                          name={null}
                          collapsed={1}
                          enableClipboard={true}
                          displayDataTypes={false}
                        />
                      </CardContent>
                    </Card>
                  )
                })}
              </Box>
            ) : (
              <Typography color="text.secondary">No responses yet. Submit a request to see results.</Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

export default OnlineEvaluation
