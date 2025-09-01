import React, { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Col, Container, Form, InputGroup, Row, Tab, Tabs } from 'react-bootstrap'
import { ComputeResponse, computeApi } from './api'

type Triplet = [number, number, number?]

const LS_KEY = 'pop_fly/saved-start'

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
  const [startZ, setStartZ] = useState('')
  const [endE, setEndE] = useState('')
  const [endN, setEndN] = useState('')
  const [endZ, setEndZ] = useState('')
  const [precision, setPrecision] = useState(0)
  const [useSavedStart, setUseSavedStart] = useState(true)
  const [savedStart, setSavedStart] = useState<number[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ComputeResponse | null>(null)

  // Load saved start
  useEffect(() => {
    const raw = localStorage.getItem(LS_KEY)
  if (raw) {
      try {
        const arr = JSON.parse(raw) as number[]
        if (Array.isArray(arr) && (arr.length === 2 || arr.length === 3)) {
          setStartE(arr[0]?.toString() ?? '')
          setStartN(arr[1]?.toString() ?? '')
          setStartZ((arr[2] ?? '').toString())
      setSavedStart(arr)
        }
      } catch {}
    }
  }, [])

  const startArray = useMemo(() => {
    const e = parseNum(startE)
    const n = parseNum(startN)
    const z = parseNum(startZ)
    const arr: number[] = []
    if (e !== undefined && n !== undefined) {
      arr.push(e, n)
      if (startZ.trim() !== '' && z !== undefined) arr.push(z)
    }
    return arr
  }, [startE, startN, startZ])

  const endArray = useMemo(() => {
    const e = parseNum(endE)
    const n = parseNum(endN)
    const z = parseNum(endZ)
    const arr: number[] = []
    if (e !== undefined && n !== undefined) {
      arr.push(e, n)
      if (endZ.trim() !== '' && z !== undefined) arr.push(z)
    }
    return arr
  }, [endE, endN, endZ])

  const effectiveStart = useMemo(() => {
    if (useSavedStart && startArray.length < 2 && savedStart && savedStart.length >= 2) {
      return savedStart
    }
    return startArray
  }, [useSavedStart, startArray, savedStart])

  const canCompute = effectiveStart.length >= 2 && endArray.length >= 2

  const onCompute = async () => {
    setError(null)
    setResult(null)
    if (!canCompute) {
      setError('Please enter valid numeric coordinates for start and end (E,N[,Z]).')
      return
    }
    setBusy(true)
    try {
  const res = await computeApi({ start: effectiveStart, end: endArray, precision })
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
    setEndZ('')
  }

  const onSaveStart = () => {
    if (startArray.length < 2) {
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
        if (result.slant_distance_m !== undefined && result.delta_z_m !== undefined) {
          const sl = result.slant_distance_m.toFixed(precision)
          const dz = signFmt(result.delta_z_m, precision)
          return `Distance: ${dist} m | Azimuth: ${az} mils | Slant: ${sl} m | ΔZ: ${dz} m`
        }
        return `Distance: ${dist} m | Azimuth: ${az} mils`
      })()
    : ''

  return (
    <Container className="py-4">
  <h1 className="mb-3">pop_fly</h1>
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
                <Form.Label>Easting (m)</Form.Label>
                <Form.Control value={startE} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStartE(e.target.value)} placeholder="E" />
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId="startN">
                <Form.Label>Northing (m)</Form.Label>
                <Form.Control value={startN} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStartN(e.target.value)} placeholder="N" />
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId="startZ">
                <Form.Label>Elevation Z (m)</Form.Label>
                <Form.Control value={startZ} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStartZ(e.target.value)} placeholder="Z (optional)" />
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
                <Form.Label>Easting (m)</Form.Label>
                <Form.Control value={endE} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEndE(e.target.value)} placeholder="E" />
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId="endN">
                <Form.Label>Northing (m)</Form.Label>
                <Form.Control value={endN} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEndN(e.target.value)} placeholder="N" />
              </Form.Group>
            </Col>
            <Col>
              <Form.Group controlId="endZ">
                <Form.Label>Elevation Z (m)</Form.Label>
                <Form.Control value={endZ} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEndZ(e.target.value)} placeholder="Z (optional)" />
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
