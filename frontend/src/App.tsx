import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { AppShell } from './components/AppShell'
import PatientOverview from './pages/PatientOverview'
import FocalScroll from './pages/FocalScroll'
import Timeline from './pages/Timeline'
import Comparison from './pages/Comparison'

export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<Navigate to="/patients/patient1" replace />} />
          <Route path="/patients/:patientId" element={<PatientOverview />} />
          <Route
            path="/patients/:patientId/compare"
            element={<Comparison />}
          />
          <Route
            path="/patients/:patientId/embryos/:embryoLabel/timepoints/:timepoint"
            element={<FocalScroll />}
          />
          <Route
            path="/patients/:patientId/embryos/:embryoLabel/timeline"
            element={<Timeline />}
          />
        </Routes>
      </AppShell>
    </BrowserRouter>
  )
}
