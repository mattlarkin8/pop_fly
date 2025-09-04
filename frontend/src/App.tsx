import React, { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Col, Container, Form, Row, Tab, Tabs } from 'react-bootstrap'
import { ComputeResponse, computeApi } from './api'

const LS_KEY = 'pop_fly/saved-start'

type Pair = [number | string, number | string]

function isPair(v: unknown): v is Pair {
  return Array.isArray(v) && v.length === 2 &&
    (typeof v[0] === 'string' || typeof v[0] === 'number') &&
    (typeof v[1] === 'string' || typeof v[1] === 'number')
}

function parseNum(v: string): number | undefined {
  if (v.trim() === '') return undefined
  const n = Number(v)
  return Number.isFinite(n) ? n : undefined
}

function signFmt(n: number, precision: number) {
  const s = n >= 0 ? '+' : '-'
  return `${s}${Math.abs(n).toFixed(precision)}`
}

export default function App() {
  const [startE, setStartE] = useState('')
  const [startN, setStartN] = useState('')
  // 2D only
  const [endE, setEndE] = useState('')
  const [endN, setEndN] = useState('')
  const [precision, setPrecision] = useState(0)
  const [useSavedStart, setUseSavedStart] = useState(true)
  const [savedStart, setSavedStart] = useState<Pair | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ComputeResponse | null>(null)

  // Load saved start
  useEffect(() => {
    const raw = localStorage.getItem(LS_KEY)
    if (raw) {
      try {
        const arr = JSON.parse(raw) as unknown
        if (Array.isArray(arr) && arr.length === 2) {
          // Normalize displayed fields to strings
          setStartE((arr[0] as any)?.toString() ?? '')
          setStartN((arr[1] as any)?.toString() ?? '')
          // Use type guard to set savedStart safely; fall back to string pair
          if (isPair(arr)) {
            setSavedStart(arr)
          } else {
            setSavedStart([ (arr[0] as any)?.toString() ?? '', (arr[1] as any)?.toString() ?? '' ])
          }
        }
      } catch {}
    }
  }, [])

  const startArray = useMemo<Pair | null>(() => {
    const eStr = startE.trim()
    const nStr = startN.trim()
    if (eStr !== '' && nStr !== '') {
      return [eStr, nStr]
    }
    return null
  }, [startE, startN])

  const endArray = useMemo<Pair | null>(() => {
    const eStr = endE.trim()
    const nStr = endN.trim()
    if (eStr !== '' && nStr !== '') {
      return [eStr, nStr]
    }
    return null
  }, [endE, endN])

  const effectiveStart = useMemo<Pair | null>(() => {
    if (useSavedStart && (startArray === null) && savedStart) {
      return savedStart
    }
    return startArray
  }, [useSavedStart, startArray, savedStart])

  const canCompute = effectiveStart !== null && endArray !== null

  const onCompute = async () => {
    setError(null)
    setResult(null)
    if (!canCompute) {
      setError('Please enter valid numeric coordinates for start and end (E,N).')
      return
    }
    setBusy(true)
    try {
  // effectiveStart and endArray are narrowed by canCompute
  const res = await computeApi({ start: effectiveStart as Pair, end: endArray as Pair, precision })
      setResult(res)
    } catch (e: any) {
      setError(e?.message || 'Request failed')
    } finally {
      setBusy(false)
    }
  }

  const onClear = () => {
    setError(null)
    setResult(null)
    setEndE('')
    setEndN('')
  }

  const onSaveStart = () => {
  if (!isPair(startArray)) {
      setError('Cannot save start: please enter at least E and N.')
      return
    }
  localStorage.setItem(LS_KEY, JSON.stringify(startArray))
  setSavedStart(startArray)
  }

  const hr = result
    ? (() => {
        const dist = result.distance_m.toFixed(precision)
        const az = result.azimuth_mils.toFixed(1)
        return `Distance: ${dist} m | Azimuth: ${az} mils`
      })()
    : ''

  return (
    <Container className="py-4">
      <h1 className="mb-3">Pop Fly</h1>
      {error && (
        <Alert variant="danger" onClose={() => setError(null)} dismissible>
          {error}
        </Alert>
      )}
      <Row className="g-3">
        <Col md={6}>
          <h5>Start</h5>
          <Row className="g-2">
            <Col>
              <Form.Group controlId="startE">
                <Form.Label>Easting (digits or meters)</Form.Label>
                <Form.Control value={startE} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStartE(e.target.value)} placeholder="E" />
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId="startN">
                <Form.Label>Northing (digits or meters)</Form.Label>
                <Form.Control value={startN} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStartN(e.target.value)} placeholder="N" />
              </Form.Group>
            </Col>
          </Row>
          <div className="mt-2 d-flex gap-2">
            <Button variant="secondary" onClick={onSaveStart}>Save start</Button>
            <Form.Check
              type="switch"
              id="useSavedStart"
              label="Use saved start"
              checked={useSavedStart}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUseSavedStart(e.currentTarget.checked)}
            />
          </div>
        </Col>
        <Col md={6}>
          <h5>End</h5>
          <Row className="g-2">
            <Col>
              <Form.Group controlId="endE">
                <Form.Label>Easting (digits or meters)</Form.Label>
                <Form.Control value={endE} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEndE(e.target.value)} placeholder="E" />
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId="endN">
                <Form.Label>Northing (digits or meters)</Form.Label>
                <Form.Control value={endN} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEndN(e.target.value)} placeholder="N" />
              </Form.Group>
            </Col>
          </Row>
        </Col>
      </Row>
      <Row className="g-3 mt-3">
        <Col md={4}>
          <Form.Group controlId="precision">
            <Form.Label>Precision (decimals for meters)</Form.Label>
            <Form.Control
              type="number"
              min={0}
              max={6}
              value={precision}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPrecision(Math.max(0, Math.min(6, Number(e.target.value))))}
            />
          </Form.Group>
        </Col>
      </Row>
      <div className="mt-3 d-flex gap-2">
        <Button onClick={onCompute} disabled={busy || !canCompute}>Compute</Button>
        <Button variant="outline-secondary" onClick={onClear} disabled={busy}>Clear</Button>
      </div>

      {result && (
        <div className="mt-4">
          <h5>Result</h5>
          <Alert variant="success">{hr}</Alert>
          <Tabs defaultActiveKey="human" className="mb-3">
            <Tab eventKey="human" title="Human-readable">
              <pre style={{ whiteSpace: 'pre-wrap' }}>{hr}</pre>
            </Tab>
            <Tab eventKey="json" title="JSON">
              <pre>{JSON.stringify(result, null, 2)}</pre>
            </Tab>
          </Tabs>
        </div>
      )}
    </Container>
  )
}