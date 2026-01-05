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
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Card,
  CardContent,
  IconButton,
  Chip,
} from '@mui/material'
import { Delete as DeleteIcon, CloudUpload as UploadIcon, Save as SaveIcon } from '@mui/icons-material'
import ReactJson from '@microlink/react-json-view'
import { onlineEvaluation } from '../services/api'

const GEMINI_MODELS = [
  'gemini-2.5-pro',
  'gemini-2.5-flash',
  'gemini-2.5-flash-lite',
  'gemini-3.0-pro',
  'gemini-3.0-flash',
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

  const handleFileUpload = (event) => {
    const file = event.target.files[0]
    if (file) {
      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          // Try to parse as JSON first
          const content = JSON.parse(e.target.result)
          setGeminiRequest(JSON.stringify(content, null, 2))

          // Extract system instruction if present
          if (content.system_instruction) {
            setSystemInstruction(content.system_instruction.replace(/\\n/g, '\n'))
          }
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

  const handleSubmit = async () => {
    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      // Parse and validate inputs
      let parsedRequest = {}
      if (geminiRequest.trim()) {
        // Try to parse as JSON first, if it fails treat as plain string
        try {
          parsedRequest = JSON.parse(geminiRequest)
        } catch (jsonError) {
          // Not valid JSON, treat as plain text string
          parsedRequest = geminiRequest.trim()
        }
      }

      let parsedConfig = null
      if (geminiConfig.trim()) {
        parsedConfig = JSON.parse(geminiConfig)
      }

      const finalModel = model === 'custom' ? customModel : model

      const data = {
        gemini_request: parsedRequest,
        system_instruction: systemInstruction || null,
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
              label="Gemini Request (JSON)"
              multiline
              rows={8}
              fullWidth
              value={geminiRequest}
              onChange={(e) => setGeminiRequest(e.target.value)}
              sx={{ mb: 2 }}
              helperText="Paste or upload your Gemini API request JSON"
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
              helperText='e.g., {"temperature": 0.7, "top_k": 40}'
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
            >
              {loading ? <CircularProgress size={24} /> : 'Submit'}
            </Button>
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

            {responses.length > 0 ? (
              <Box>
                {responses.map((response, index) => (
                  <Card key={index} sx={{ mb: 2 }}>
                    <CardContent>
                      <Typography variant="subtitle2" gutterBottom>
                        Response {index + 1}
                      </Typography>
                      <ReactJson
                        src={response}
                        name={null}
                        collapsed={1}
                        enableClipboard={true}
                        displayDataTypes={false}
                      />
                    </CardContent>
                  </Card>
                ))}
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
