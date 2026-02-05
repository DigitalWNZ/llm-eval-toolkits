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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Link,
  Stepper,
  Step,
  StepLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import { batchEvaluation } from '../services/api'

const GEMINI_MODELS = [
  'gemini-2.5-pro',
  'gemini-2.5-flash',
  'gemini-2.5-flash-lite',
  'gemini-3-pro-preview',
  'gemini-3-flash-preview',
  'gemini-3.0-flash-lite',
]

function BatchEvaluation() {
  const [activeStep, setActiveStep] = useState(0)
  const [inputFolder, setInputFolder] = useState('')
  const [expectedFolder, setExpectedFolder] = useState('')
  const [outputFolder, setOutputFolder] = useState('')
  const [geminiConfig, setGeminiConfig] = useState('')
  const [model, setModel] = useState('gemini-2.5-flash')
  const [customModel, setCustomModel] = useState('')
  const [project, setProject] = useState('')
  const [iterations, setIterations] = useState(1)
  const [mappings, setMappings] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [submitResult, setSubmitResult] = useState(null)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewData, setPreviewData] = useState({
    inputRequest: '',
    expectedOutput: '',
    outputFiles: [],
  })
  const [evaluationDetailOpen, setEvaluationDetailOpen] = useState(false)
  const [selectedEvaluation, setSelectedEvaluation] = useState(null)
  const [evaluationResults, setEvaluationResults] = useState([]) // Array of evaluation results
  const [actualOutputFolder, setActualOutputFolder] = useState('') // Store actual output folder used
  const [evaluationFileContents, setEvaluationFileContents] = useState({
    inputRequest: 'Loading...',
    expectedOutput: 'Loading...',
    outputFile: 'Loading...',
  })
  const [outputFilesExist, setOutputFilesExist] = useState(false)
  const [checkingOutputFiles, setCheckingOutputFiles] = useState(false)
  const [evaluatingFromMapping, setEvaluatingFromMapping] = useState(false)
  /*
   * Expected evaluationResults data structure:
   * [
   *   {
   *     input_request: "request.json",
   *     expected_output: "expected.json",
   *     output_file: "output_1.json",
   *     similarity_score: 85,  // 0-100
   *     dimension_scores: {
   *       semantic_similarity: 35,  // out of 40
   *       structural_consistency: 20,  // out of 25
   *       key_information_preservation: 22,  // out of 25
   *       response_quality: 8  // out of 10
   *     },
   *     key_differences: [
   *       {
   *         category: "semantic",
   *         description: "Parameter value mismatch",
   *         severity: "major",
   *         location: "function_call.parameters.city"
   *       }
   *     ],
   *     strengths: ["Correct function name", "Proper JSON structure"],
   *     overall_assessment: "The output is highly similar to expected..."
   *   }
   * ]
   */

  const handleProcessRequest = async () => {
    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      let parsedConfig = null
      if (geminiConfig.trim()) {
        parsedConfig = JSON.parse(geminiConfig)
      }

      const finalModel = model === 'custom' ? customModel : model

      const data = {
        input_folder: inputFolder,
        expected_folder: expectedFolder,
        output_folder: outputFolder || null,
        gemini_config: parsedConfig,
        model: finalModel,
        project: project,
        iterations: iterations,
      }

      const result = await batchEvaluation.getMapping(data)
      setMappings(result.mappings)
      setSuccess(result.message)
      setActiveStep(1)

      // Check if output files exist
      checkOutputFilesExist(result.mappings, outputFolder)
    } catch (err) {
      setError('Error: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const checkOutputFilesExist = async (mappings, outputFolderPath) => {
    if (!outputFolderPath) {
      setOutputFilesExist(false)
      return
    }

    setCheckingOutputFiles(true)
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

    try {
      // Check if all output files exist
      let allExist = true
      for (const mapping of mappings) {
        for (const outputFile of mapping.output_files) {
          try {
            const response = await fetch(
              `${baseUrl}/api/batch/preview?folder=${encodeURIComponent('')}&file=${encodeURIComponent(outputFile)}`
            )
            if (!response.ok) {
              allExist = false
              break
            }
          } catch (err) {
            allExist = false
            break
          }
        }
        if (!allExist) break
      }

      setOutputFilesExist(allExist)
      setActualOutputFolder(outputFolderPath)
    } catch (err) {
      setOutputFilesExist(false)
    } finally {
      setCheckingOutputFiles(false)
    }
  }

  const handleEvaluateFromMapping = async () => {
    setError(null)
    setSuccess(null)
    setEvaluatingFromMapping(true)

    try {
      const finalModel = model === 'custom' ? customModel : model

      const data = {
        input_folder: inputFolder,
        expected_folder: expectedFolder,
        output_folder: actualOutputFolder,
        model: finalModel,
        project: project,
        pass_threshold: 75,
      }

      const result = await batchEvaluation.evaluate(data)
      setEvaluationResults(result.evaluation_results)
      setSuccess(result.message)

      // Create a mock submitResult to display in step 3
      setSubmitResult({
        total_processed: result.evaluation_results.length,
        successful: result.evaluation_results.length,
        failed: 0,
        output_folder: actualOutputFolder,
      })

      setActiveStep(2)
    } catch (err) {
      setError('Error: ' + (err.response?.data?.detail || err.message))
    } finally {
      setEvaluatingFromMapping(false)
    }
  }

  const handleSubmit = async () => {
    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      let parsedConfig = null
      if (geminiConfig.trim()) {
        parsedConfig = JSON.parse(geminiConfig)
      }

      const finalModel = model === 'custom' ? customModel : model

      const data = {
        input_folder: inputFolder,
        expected_folder: expectedFolder,
        output_folder: outputFolder || null,
        gemini_config: parsedConfig,
        model: finalModel,
        project: project,
        iterations: iterations,
      }

      const result = await batchEvaluation.submit(data)
      setSubmitResult(result)
      setActualOutputFolder(result.output_folder) // Store actual output folder
      setSuccess(`Completed: ${result.successful} successful, ${result.failed} failed`)
      setActiveStep(2)
    } catch (err) {
      setError('Error: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleEvaluate = async () => {
    setError(null)
    setSuccess(null)
    setLoading(true)

    try {
      const finalModel = model === 'custom' ? customModel : model

      const data = {
        input_folder: inputFolder,
        expected_folder: expectedFolder,
        output_folder: actualOutputFolder,
        model: finalModel,
        project: project,
        pass_threshold: 75,
      }

      const result = await batchEvaluation.evaluate(data)
      setEvaluationResults(result.evaluation_results)
      setSuccess(result.message)
    } catch (err) {
      setError('Error: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleImportResults = (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const importedData = JSON.parse(e.target.result)

        // Restore metadata to form fields
        if (importedData.metadata) {
          setInputFolder(importedData.metadata.input_folder || '')
          setExpectedFolder(importedData.metadata.expected_folder || '')
          setActualOutputFolder(importedData.metadata.output_folder || '')
          setOutputFolder(importedData.metadata.output_folder || '')
          setProject(importedData.metadata.project || '')

          // Restore model
          const importedModel = importedData.metadata.model || 'gemini-2.5-flash'
          if (GEMINI_MODELS.includes(importedModel)) {
            setModel(importedModel)
          } else {
            setModel('custom')
            setCustomModel(importedModel)
          }
        }

        // Restore results
        if (importedData.evaluation_results) {
          setEvaluationResults(importedData.evaluation_results)
        }

        // Restore processing summary
        if (importedData.processing_summary) {
          setSubmitResult({
            total_processed: importedData.processing_summary.total_processed,
            successful: importedData.processing_summary.successful,
            failed: importedData.processing_summary.failed,
            output_folder: importedData.metadata?.output_folder || '',
          })
        }

        // Navigate to results page
        setActiveStep(2)
        setSuccess('Previous evaluation results imported successfully')
      } catch (err) {
        setError('Error importing file: ' + err.message)
      }
    }
    reader.readAsText(file)

    // Reset the input so the same file can be selected again
    event.target.value = ''
  }

  const handleSaveResults = () => {
    const scoreRanges = calculateScoreRanges()

    const saveData = {
      metadata: {
        timestamp: new Date().toISOString(),
        input_folder: inputFolder,
        expected_folder: expectedFolder,
        output_folder: actualOutputFolder,
        model: model === 'custom' ? customModel : model,
        project: project,
      },
      processing_summary: {
        total_processed: submitResult?.total_processed || 0,
        successful: submitResult?.successful || 0,
        failed: submitResult?.failed || 0,
      },
      score_distribution: {
        excellent_90_100: scoreRanges.excellent.count,
        good_75_89: scoreRanges.good.count,
        moderate_60_74: scoreRanges.moderate.count,
        fair_40_59: scoreRanges.fair.count,
        poor_20_39: scoreRanges.poor.count,
        failing_0_19: scoreRanges.failing.count,
      },
      evaluation_results: evaluationResults,
    }

    const blob = new Blob([JSON.stringify(saveData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
    a.download = `batch_evaluation_results_${timestamp}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleBack = () => {
    setActiveStep(0)
    setMappings([])
    setSubmitResult(null)
  }

  const handlePreview = async (mapping) => {
    setPreviewOpen(true)

    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const newPreviewData = {
      inputRequest: 'Loading...',
      expectedOutput: mapping.has_expected ? 'Loading...' : 'No expected output file',
      outputFiles: [],
    }
    setPreviewData(newPreviewData)

    try {
      // Load input request
      const inputResponse = await fetch(
        `${baseUrl}/api/batch/preview?folder=${encodeURIComponent(inputFolder)}&file=${encodeURIComponent(
          mapping.input_request
        )}`
      )
      if (inputResponse.ok) {
        const inputData = await inputResponse.json()
        newPreviewData.inputRequest = JSON.stringify(inputData, null, 2)
      } else {
        newPreviewData.inputRequest = 'Error loading input request'
      }

      // Load expected output if it exists
      if (mapping.has_expected) {
        const expectedResponse = await fetch(
          `${baseUrl}/api/batch/preview?folder=${encodeURIComponent(expectedFolder)}&file=${encodeURIComponent(
            mapping.expected_output
          )}`
        )
        if (expectedResponse.ok) {
          const expectedData = await expectedResponse.json()
          newPreviewData.expectedOutput = JSON.stringify(expectedData, null, 2)
        } else {
          newPreviewData.expectedOutput = 'Error loading expected output'
        }
      }

      // Load output files if they exist
      for (const outputFile of mapping.output_files) {
        try {
          const outputResponse = await fetch(
            `${baseUrl}/api/batch/preview?folder=${encodeURIComponent('')}&file=${encodeURIComponent(outputFile)}`
          )
          if (outputResponse.ok) {
            const outputData = await outputResponse.json()
            newPreviewData.outputFiles.push({
              path: outputFile,
              content: JSON.stringify(outputData, null, 2),
            })
          }
        } catch (err) {
          // Output file doesn't exist yet, skip
        }
      }

      setPreviewData({ ...newPreviewData })
    } catch (err) {
      setPreviewData({
        inputRequest: `Error: ${err.message}`,
        expectedOutput: 'Error loading',
        outputFiles: [],
      })
    }
  }

  const handleClosePreview = () => {
    setPreviewOpen(false)
    setPreviewData({
      inputRequest: '',
      expectedOutput: '',
      outputFiles: [],
    })
  }

  const handleViewEvaluationDetail = async (evaluation) => {
    setSelectedEvaluation(evaluation)
    setEvaluationDetailOpen(true)
    setEvaluationFileContents({
      inputRequest: 'Loading...',
      expectedOutput: 'Loading...',
      outputFile: 'Loading...',
    })

    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

    try {
      // Load input request
      const inputResponse = await fetch(
        `${baseUrl}/api/batch/preview?folder=${encodeURIComponent(inputFolder)}&file=${encodeURIComponent(
          evaluation.input_request
        )}`
      )
      let inputContent = 'Error loading input request'
      if (inputResponse.ok) {
        const inputData = await inputResponse.json()
        inputContent = JSON.stringify(inputData, null, 2)
      }

      // Load expected output
      let expectedContent = 'No expected output'
      if (evaluation.expected_output) {
        const expectedResponse = await fetch(
          `${baseUrl}/api/batch/preview?folder=${encodeURIComponent(expectedFolder)}&file=${encodeURIComponent(
            evaluation.expected_output
          )}`
        )
        if (expectedResponse.ok) {
          const expectedData = await expectedResponse.json()
          expectedContent = JSON.stringify(expectedData, null, 2)
        } else {
          expectedContent = 'Error loading expected output'
        }
      }

      // Load output file
      const outputResponse = await fetch(
        `${baseUrl}/api/batch/preview?folder=${encodeURIComponent('')}&file=${encodeURIComponent(
          actualOutputFolder + '/' + evaluation.output_file
        )}`
      )
      let outputContent = 'Error loading output file'
      if (outputResponse.ok) {
        const outputData = await outputResponse.json()
        outputContent = JSON.stringify(outputData, null, 2)
      }

      setEvaluationFileContents({
        inputRequest: inputContent,
        expectedOutput: expectedContent,
        outputFile: outputContent,
      })
    } catch (err) {
      setEvaluationFileContents({
        inputRequest: `Error: ${err.message}`,
        expectedOutput: `Error: ${err.message}`,
        outputFile: `Error: ${err.message}`,
      })
    }
  }

  const handleCloseEvaluationDetail = () => {
    setEvaluationDetailOpen(false)
    setSelectedEvaluation(null)
  }

  const calculateScoreRanges = () => {
    const ranges = {
      'excellent': { label: '90-100 (Excellent)', count: 0, color: '#4caf50' },
      'good': { label: '75-89 (Good)', count: 0, color: '#8bc34a' },
      'moderate': { label: '60-74 (Moderate)', count: 0, color: '#ffeb3b' },
      'fair': { label: '40-59 (Fair)', count: 0, color: '#ff9800' },
      'poor': { label: '20-39 (Poor)', count: 0, color: '#ff5722' },
      'failing': { label: '0-19 (Failing)', count: 0, color: '#f44336' },
    }

    evaluationResults.forEach((result) => {
      const score = result.similarity_score
      if (score >= 90) ranges.excellent.count++
      else if (score >= 75) ranges.good.count++
      else if (score >= 60) ranges.moderate.count++
      else if (score >= 40) ranges.fair.count++
      else if (score >= 20) ranges.poor.count++
      else ranges.failing.count++
    })

    return ranges
  }

  const getScoreColor = (score) => {
    if (score >= 90) return 'success'
    if (score >= 75) return 'info'
    if (score >= 60) return 'warning'
    return 'error'
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Batch Evaluation
      </Typography>

      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        <Step>
          <StepLabel>Configure</StepLabel>
        </Step>
        <Step>
          <StepLabel>Review Mapping</StepLabel>
        </Step>
        <Step>
          <StepLabel>Results</StepLabel>
        </Step>
      </Stepper>

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

      {/* Step 1: Configuration */}
      {activeStep === 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Batch Configuration
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <TextField
                label="Input Request Folder (folder_A)"
                fullWidth
                required
                value={inputFolder}
                onChange={(e) => setInputFolder(e.target.value)}
                helperText="Absolute path to folder containing request JSON files (max 10 files)"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                label="Expected Output Folder (folder_B)"
                fullWidth
                required
                value={expectedFolder}
                onChange={(e) => setExpectedFolder(e.target.value)}
                helperText="Absolute path to folder with expected outputs"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                label="Output Folder (folder_C)"
                fullWidth
                value={outputFolder}
                onChange={(e) => setOutputFolder(e.target.value)}
                helperText="Optional: defaults to {folder_A}_output_{timestamp}"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                label="Gemini Configuration (JSON)"
                fullWidth
                multiline
                rows={3}
                value={geminiConfig}
                onChange={(e) => setGeminiConfig(e.target.value)}
                helperText='Optional config overrides, e.g., {"temperature": 0.7}'
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <FormControl fullWidth required>
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
            </Grid>

            {model === 'custom' && (
              <Grid item xs={12} md={4}>
                <TextField
                  label="Custom Model Name"
                  fullWidth
                  value={customModel}
                  onChange={(e) => setCustomModel(e.target.value)}
                />
              </Grid>
            )}

            <Grid item xs={12} md={4}>
              <TextField
                label="GCP Project ID"
                fullWidth
                required
                value={project}
                onChange={(e) => setProject(e.target.value)}
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <TextField
                label="Iterations per Request"
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

            <Grid item xs={12}>
              <Button
                variant="contained"
                size="large"
                onClick={handleProcessRequest}
                disabled={loading || !inputFolder || !expectedFolder || !project}
                fullWidth
              >
                {loading ? <CircularProgress size={24} /> : 'Process Request'}
              </Button>
            </Grid>

            <Grid item xs={12}>
              <Typography variant="body2" align="center" sx={{ my: 1 }}>
                OR
              </Typography>
              <Button
                variant="outlined"
                size="large"
                component="label"
                fullWidth
              >
                Import Previous Evaluation Results
                <input
                  type="file"
                  hidden
                  accept=".json"
                  onChange={handleImportResults}
                />
              </Button>
            </Grid>
          </Grid>
        </Paper>
      )}

      {/* Step 2: Mapping Review */}
      {activeStep === 1 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            File Mapping Review
          </Typography>

          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Input Request</TableCell>
                  <TableCell>Expected Output</TableCell>
                  <TableCell>Output Files</TableCell>
                  <TableCell>Preview</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {mappings.map((mapping, index) => (
                  <TableRow key={index}>
                    <TableCell>{mapping.input_request}</TableCell>
                    <TableCell>
                      {mapping.has_expected ? (
                        mapping.expected_output
                      ) : (
                        <Typography color="error" fontWeight="bold">
                          no mapping
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Box>
                        {mapping.output_files.map((file, i) => (
                          <Typography key={i} variant="body2">
                            {file}
                          </Typography>
                        ))}
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Link
                        href="#"
                        onClick={(e) => {
                          e.preventDefault()
                          handlePreview(mapping)
                        }}
                        sx={{ cursor: 'pointer' }}
                      >
                        Preview
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {checkingOutputFiles && (
            <Alert severity="info" sx={{ mt: 2 }}>
              Checking if output files exist...
            </Alert>
          )}

          {!checkingOutputFiles && outputFilesExist && (
            <Alert severity="success" sx={{ mt: 2 }}>
              All output files exist! You can evaluate results directly without re-running the batch.
            </Alert>
          )}

          {!checkingOutputFiles && !outputFilesExist && outputFolder && (
            <Alert severity="info" sx={{ mt: 2 }}>
              Output files not found. You need to submit the batch first to generate outputs.
            </Alert>
          )}

          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button onClick={handleBack}>Back</Button>
            <Button
              variant="outlined"
              onClick={handleEvaluateFromMapping}
              disabled={!outputFilesExist || evaluatingFromMapping || checkingOutputFiles || loading}
              sx={{ flexGrow: 1 }}
            >
              {evaluatingFromMapping ? <CircularProgress size={24} /> : 'Evaluate Results'}
            </Button>
            <Button variant="contained" onClick={handleSubmit} disabled={loading || evaluatingFromMapping} sx={{ flexGrow: 1 }}>
              {loading ? <CircularProgress size={24} /> : 'Submit Batch'}
            </Button>
          </Box>
        </Paper>
      )}

      {/* Step 3: Results */}
      {activeStep === 2 && submitResult && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Batch Evaluation Results
          </Typography>

          {/* Processing Summary */}
          <Typography variant="subtitle1" sx={{ mt: 3, mb: 2, fontWeight: 'bold' }}>
            Processing Summary
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, bgcolor: 'primary.light' }}>
                <Typography variant="h4" align="center">
                  {submitResult.total_processed}
                </Typography>
                <Typography variant="body2" align="center">
                  Total Processed
                </Typography>
              </Paper>
            </Grid>

            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, bgcolor: 'success.light' }}>
                <Typography variant="h4" align="center">
                  {submitResult.successful}
                </Typography>
                <Typography variant="body2" align="center">
                  Successful
                </Typography>
              </Paper>
            </Grid>

            <Grid item xs={12} md={4}>
              <Paper sx={{ p: 2, bgcolor: 'error.light' }}>
                <Typography variant="h4" align="center">
                  {submitResult.failed}
                </Typography>
                <Typography variant="body2" align="center">
                  Failed
                </Typography>
              </Paper>
            </Grid>
          </Grid>

          {/* Score Range Summary */}
          {evaluationResults.length > 0 && (
            <>
              <Typography variant="subtitle1" sx={{ mt: 4, mb: 2, fontWeight: 'bold' }}>
                Score Distribution
              </Typography>
              <Grid container spacing={2}>
                {Object.entries(calculateScoreRanges()).map(([key, range]) => (
                  <Grid item xs={12} sm={6} md={2} key={key}>
                    <Paper
                      sx={{
                        p: 2,
                        bgcolor: range.color,
                        color: key === 'moderate' ? '#000' : '#fff',
                      }}
                    >
                      <Typography variant="h4" align="center">
                        {range.count}
                      </Typography>
                      <Typography variant="body2" align="center" sx={{ fontSize: '0.75rem' }}>
                        {range.label}
                      </Typography>
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </>
          )}

          {/* Detailed Evaluation Table */}
          <Typography variant="subtitle1" sx={{ mt: 4, mb: 2, fontWeight: 'bold' }}>
            Detailed Evaluation Results
          </Typography>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Input Request</TableCell>
                  <TableCell>Expected Output</TableCell>
                  <TableCell>Output File</TableCell>
                  <TableCell align="center">Similarity Score</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {evaluationResults.map((result, index) => (
                  <TableRow key={index}>
                    <TableCell>{result.input_request}</TableCell>
                    <TableCell>
                      {result.expected_output || (
                        <Typography color="error" fontWeight="bold">
                          no mapping
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{result.output_file}</TableCell>
                    <TableCell align="center">
                      <Link
                        href="#"
                        onClick={(e) => {
                          e.preventDefault()
                          handleViewEvaluationDetail(result)
                        }}
                        sx={{
                          cursor: 'pointer',
                          color: getScoreColor(result.similarity_score) + '.main',
                          fontWeight: 'bold',
                          fontSize: '1rem',
                        }}
                      >
                        {result.similarity_score}%
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {evaluationResults.length === 0 && (
            <Alert severity="info" sx={{ mt: 2 }}>
              No evaluation results available. Click "Evaluate Results" to compare outputs with expected results.
            </Alert>
          )}

          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button variant="contained" onClick={handleEvaluate} disabled={loading} sx={{ flexGrow: 1 }}>
              {loading ? <CircularProgress size={24} /> : 'Evaluate Results'}
            </Button>
            <Button
              variant="contained"
              color="success"
              onClick={handleSaveResults}
              disabled={evaluationResults.length === 0}
              sx={{ flexGrow: 1 }}
            >
              Save Results
            </Button>
            <Button variant="outlined" onClick={handleBack}>
              Start New Batch
            </Button>
          </Box>
        </Paper>
      )}

      {/* Preview Dialog */}
      <Dialog open={previewOpen} onClose={handleClosePreview} maxWidth="lg" fullWidth>
        <DialogTitle>File Preview</DialogTitle>
        <DialogContent>
          <Grid container spacing={2}>
            {/* Input Request */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Input Request
              </Typography>
              <Box
                component="pre"
                sx={{
                  bgcolor: 'grey.100',
                  p: 2,
                  borderRadius: 1,
                  overflow: 'auto',
                  maxHeight: '30vh',
                  fontSize: '0.75rem',
                }}
              >
                {previewData.inputRequest}
              </Box>
            </Grid>

            {/* Expected Output */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Expected Output
              </Typography>
              <Box
                component="pre"
                sx={{
                  bgcolor: 'grey.100',
                  p: 2,
                  borderRadius: 1,
                  overflow: 'auto',
                  maxHeight: '30vh',
                  fontSize: '0.75rem',
                }}
              >
                {previewData.expectedOutput}
              </Box>
            </Grid>

            {/* Output Files */}
            <Grid item xs={12}>
              <Typography variant="h6" gutterBottom>
                Generated Output Files
              </Typography>
              {previewData.outputFiles.length > 0 ? (
                previewData.outputFiles.map((output, index) => (
                  <Box key={index} sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      {output.path}
                    </Typography>
                    <Box
                      component="pre"
                      sx={{
                        bgcolor: 'grey.100',
                        p: 2,
                        borderRadius: 1,
                        overflow: 'auto',
                        maxHeight: '20vh',
                        fontSize: '0.75rem',
                      }}
                    >
                      {output.content}
                    </Box>
                  </Box>
                ))
              ) : (
                <Box
                  component="pre"
                  sx={{
                    bgcolor: 'grey.100',
                    p: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: '20vh',
                    fontSize: '0.75rem',
                  }}
                >
                  Output files do not exist yet. They will be created after running the batch submission.
                </Box>
              )}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClosePreview}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Evaluation Detail Dialog */}
      <Dialog open={evaluationDetailOpen} onClose={handleCloseEvaluationDetail} maxWidth="md" fullWidth>
        <DialogTitle>
          Evaluation Details
          {selectedEvaluation && (
            <Typography variant="subtitle2" color="text.secondary">
              {selectedEvaluation.input_request} → {selectedEvaluation.output_file}
            </Typography>
          )}
        </DialogTitle>
        <DialogContent>
          {selectedEvaluation && (
            <Grid container spacing={3}>
              {/* File Contents */}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Input Request
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    bgcolor: 'grey.100',
                    p: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: '30vh',
                    fontSize: '0.75rem',
                  }}
                >
                  {evaluationFileContents.inputRequest}
                </Box>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Expected Output
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    bgcolor: 'grey.100',
                    p: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: '30vh',
                    fontSize: '0.75rem',
                  }}
                >
                  {evaluationFileContents.expectedOutput}
                </Box>
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Actual Output
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    bgcolor: 'grey.100',
                    p: 2,
                    borderRadius: 1,
                    overflow: 'auto',
                    maxHeight: '30vh',
                    fontSize: '0.75rem',
                  }}
                >
                  {evaluationFileContents.outputFile}
                </Box>
              </Grid>

              {/* Overall Score */}
              <Grid item xs={12}>
                <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
                  <Typography variant="h6" gutterBottom>
                    Overall Similarity Score
                  </Typography>
                  <Typography variant="h3" color={getScoreColor(selectedEvaluation.similarity_score)} align="center">
                    {selectedEvaluation.similarity_score}%
                  </Typography>
                </Paper>
              </Grid>

              {/* Dimension Scores */}
              {selectedEvaluation.dimension_scores && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Dimension Scores
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6} md={3}>
                      <Paper sx={{ p: 2, bgcolor: 'info.light' }}>
                        <Typography variant="body2" align="center">
                          Semantic
                        </Typography>
                        <Typography variant="h5" align="center">
                          {selectedEvaluation.dimension_scores.semantic_similarity}/40
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Paper sx={{ p: 2, bgcolor: 'info.light' }}>
                        <Typography variant="body2" align="center">
                          Structural
                        </Typography>
                        <Typography variant="h5" align="center">
                          {selectedEvaluation.dimension_scores.structural_consistency}/25
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Paper sx={{ p: 2, bgcolor: 'info.light' }}>
                        <Typography variant="body2" align="center">
                          Information
                        </Typography>
                        <Typography variant="h5" align="center">
                          {selectedEvaluation.dimension_scores.key_information_preservation}/25
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={6} md={3}>
                      <Paper sx={{ p: 2, bgcolor: 'info.light' }}>
                        <Typography variant="body2" align="center">
                          Quality
                        </Typography>
                        <Typography variant="h5" align="center">
                          {selectedEvaluation.dimension_scores.response_quality}/10
                        </Typography>
                      </Paper>
                    </Grid>
                  </Grid>
                </Grid>
              )}

              {/* Key Differences */}
              {selectedEvaluation.key_differences && selectedEvaluation.key_differences.length > 0 && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Key Differences
                  </Typography>
                  {selectedEvaluation.key_differences.map((diff, index) => (
                    <Paper
                      key={index}
                      sx={{
                        p: 2,
                        mb: 1,
                        borderLeft: 4,
                        borderColor:
                          diff.severity === 'critical'
                            ? 'error.main'
                            : diff.severity === 'major'
                            ? 'warning.main'
                            : 'info.main',
                      }}
                    >
                      <Typography variant="subtitle2" fontWeight="bold">
                        {diff.category} - {diff.severity}
                      </Typography>
                      <Typography variant="body2">{diff.description}</Typography>
                      {diff.location && (
                        <Typography variant="caption" color="text.secondary">
                          Location: {diff.location}
                        </Typography>
                      )}
                    </Paper>
                  ))}
                </Grid>
              )}

              {/* Strengths */}
              {selectedEvaluation.strengths && selectedEvaluation.strengths.length > 0 && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Strengths
                  </Typography>
                  <Box component="ul" sx={{ pl: 2 }}>
                    {selectedEvaluation.strengths.map((strength, index) => (
                      <Typography component="li" key={index} variant="body2" sx={{ mb: 0.5 }}>
                        {strength}
                      </Typography>
                    ))}
                  </Box>
                </Grid>
              )}

              {/* Overall Assessment */}
              {selectedEvaluation.overall_assessment && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Overall Assessment
                  </Typography>
                  <Paper sx={{ p: 2, bgcolor: 'grey.100' }}>
                    <Typography variant="body2">{selectedEvaluation.overall_assessment}</Typography>
                  </Paper>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseEvaluationDetail}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default BatchEvaluation
